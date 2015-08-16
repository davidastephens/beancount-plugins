"""Beancount Plugin

Automatically add depreciation entries for fixed assets.


# License: The MIT License
# Copyright (c) 2015 Alok Parlikar

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


This plugin looks at postings that have the 'depreciation' metadata, and
generates new entries until the closing of the previous year to depreciate the
value of the account on which the metadata was placed.

Currently, the following methods of depreciation are supported:
    WDV: Written Down Value
    CRA: Canadian Revenue Agency method (assets purchased in current year are allowed 50% of normal rate)

Example: -->

plugin "beancount.plugins.depreciate" "{
    'method': 'WDV',
    'year_closing_month': 12,  # Could be 3 for the fiscal year ending Mar 31.
    'halfdepr': True,  # Assets used less than 180 days will be depreciated at half the allowed rate that year
    'account': 'Expenses:Depreciation',  # Account to post depreciation entries to.
    '2010': 0.5, # Business only open for half year in 2010, adjust depreciation rate down.
    'expense_subaccount': True, #If true, will use subaccount for depreciation expense using first word in Narration.  ie: Expenses:Depreciation:Printer
    'asset_subaccount': True, #If true, will use asset subaccount for depreciation expense. ie: Assets:Fixed:Comp:Depreciation. 
}"

2014-03-02 * "" | "Printer Purchase"
  Assets:Cash                                   -100.00 INR
  Assets:Fixed:Comp                              100.00 INR
    depreciation: "Printer Depreciation @0.60"

<--

The "depreciation" metadata has this format:
  "NARRATION STRING @RATE"
The narration string here will be used in the newly generated entries.
Rate should be a number, not percentage. Use "0.60" to mean "60%".


"""

__author__ = 'Alok Parlikar <alok@parlikar.com>'

import datetime
from decimal import Decimal

from beancount.core.amount import amount_mult, amount_sub
from beancount.core import data
from beancount.core.position import Position


__plugins__ = ['depreciate']

def depreciate(entries, options_map, config):
    """Add depreciation entries for fixed assets.  See module docstring for more
    details and example"""

    config_obj = eval(config, {}, {})
    if not isinstance(config_obj, dict):
        raise RuntimeError("Invalid plugin configuration: should be a single dict.")

    depr_method = config_obj.pop('method', 'WDV')
    year_closing_month = config_obj.pop('year_closing_month', 12)
    half_depr = config_obj.pop('half_depr', True)
    depr_account = config_obj.pop('account', "Expenses:Depreciation")
    expense_subaccount = config_obj.pop('expense_subaccount', False)
    asset_subaccount = config_obj.pop('asset_subaccount', False)

    if depr_method not in ['WDV','CRA']:
        raise RuntimeError("Specified depreciation method in plugin not implemented")

    if not 0 < year_closing_month <= 12:
        raise RuntimeError("Invalid year-closing-month specified")

    errors = []
    depr_candidates = []
    for entry in entries:
        date = entry.date
        try:
            for p in entry.postings:
                if 'depreciation' in p.meta:
                    depr_candidates.append((date, p, entry))
        except (AttributeError):
            pass
    for date, posting, entry in depr_candidates:
        narration, rate = posting.meta['depreciation'].split('@')
        narration = narration.strip()
        rate = Decimal(rate)

        orig_val = posting.position.get_units()
        current_val = orig_val
        new_dates = get_closing_dates(date, year_closing_month)

        for d in new_dates:
            if depr_method == 'WDR':
                if half_depr and d - date < datetime.timedelta(180):
                    # Asset used for less than 180 days, use half the rate allowed.
                    rate_used = rate/2
                    narration_suffix = " - Half Depreciation (<180days)"
                else:
                    rate_used = rate
                    narration_suffix = ""

            elif depr_method == 'CRA':
                if half_depr and d < datetime.date(date.year+1, date.month, date.day):
                   # Asset purchased this year, use half of rate allowed
                    rate_used = rate/2
                    narration_suffix = " - Half Depreciation (Same year)"
                else:
                    rate_used = rate
                    narration_suffix = ""

            multiplier = Decimal(config_obj.get(str(d.year),1))
            rate_used = rate_used*multiplier
            current_depr = amount_mult(current_val, rate_used)

            account = posting.account
            if asset_subaccount:
                account += ":Depreciation"

            depr_account_used = depr_account
            if expense_subaccount:
                depr_account_used = depr_account + ":" + narration.split(" ")[0]

            p1 = data.Posting(account=account,
                              price=None,
                              meta=None,
                              flag=None,
                              position=Position.from_amounts(amount_mult(current_depr, Decimal(-1))))
            p2 = data.Posting(account=depr_account_used,
                              price=None,
                              meta=None,
                              flag=None,
                              position=Position.from_amounts(current_depr))

            e = entry._replace(narration=narration + narration_suffix,
                               date=d,
                               flag='*',
                               payee=None,
                               tags={'AUTO-DEPRECIATION'},
                               postings=[p1, p2])
            entries.append(e)

            current_val = amount_sub(current_val, current_depr)

    return entries, errors


def get_closing_dates(begin_date, year_closing_month):
    """Given a begin_date, find out all dates until today, where a fiscal year has
    ended."""

    today = datetime.date.today()

    if begin_date.month <= year_closing_month:
        first_closing_year = begin_date.year
    else:
        first_closing_year = begin_date.year+1

    # Calculate first closing date as the last date of the closing month that year
    first_closing_date = get_last_day_of_month(
        datetime.date(first_closing_year,
                      year_closing_month,
                      1))
    closing_dates = []
    d = first_closing_date
    while d <= today:
        closing_dates.append(d)
        d = get_last_day_of_month(datetime.date(d.year+1, year_closing_month, 1))
    return closing_dates


def get_last_day_of_month(date):
    """Given a date, find the last date of the month the date belongs to"""

    next_month = date.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)

