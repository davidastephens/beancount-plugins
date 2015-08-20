# beancount-plugins

Various user contributed plugins for [Beancount] (http://furius.ca/beancount/),
a double-entry bookkeeping computer language.

## Installation

Install via pip

```shell

   $ pip install beancount-plugins
```

## Plugins


## Automatic Depreciation

This plugin looks at postings that have the 'depreciation' metadata, and
generates new entries until the closing of the previous year to depreciate the
value of the account on which the metadata was placed.

Currently, the following methods of depreciation are supported:

    WDV: Written Down Value
    CRA: Canadian Revenue Agency method (assets purchased in current year are allowed 50% of normal rate)

Example:
```
plugin "beancount_plugins.plugins.flexible_depreciation.depreciate" "{
    'method': 'WDV',
    'year_closing_month': 12,  # Could be 3 for the fiscal year ending Mar 31.
    'halfdepr': True,  # Assets used less than 180 days will be depreciated at half the allowed rate that year
    'account': 'Expenses:Depreciation',  # Account to post depreciation entries to.
    '2010': 0.5, # Business only open for half year in 2010, adjust depreciation rate down.
    'expense_subaccount': True, #If true, will use subaccount for depreciation expense using first word in Narration.
                                #ie: Expenses:Depreciation:Printer
    'asset_subaccount': True,   #If true, will use asset subaccount for depreciation expense.
                                #ie: Assets:Fixed:Comp:Depreciation.
}"

2014-03-02 * "" | "Printer Purchase"
  Assets:Cash                                   -100.00 INR
  Assets:Fixed:Comp                              100.00 INR
    depreciation: "Printer Depreciation @0.60"
```

The "depreciation" metadata has this format:

```
  "NARRATION STRING @RATE"
```

The narration string here will be used in the newly generated entries.
Rate should be a number, not percentage. Use "0.60" to mean "60%".


## Zero Sum

Plugin for accounts that should sum up to zero. Determines transactions
that when taken together, sum up to zero, and move them to a specified
account. The remaining entries are the 'unmatched' ones, that need attention
from the user.

#### Motivation:

Real-world transfers frequently occur between accounts. For example, between a
checking account and an investment account. When double entry bookkeeping is
used to track such transfers, we end up with two problems:

    a) when account statements are converted to double-entry format, the user
    has to manually match the transfers on account statements from the two
    institutions involved, and remove one of the entries since they are
    redundant.

    b) even when (a) is done, the transfer might take a day or more to
    complete: the two accounts involved would then reflect the transfer on
    different dates.

Since the money is truly missing from all the physical accounts for the period
of transfer, they can be accounted for as shown in this example:

```
2005-01-01 Transfer
  Assets:Bank_of_Ameriplus  -20 USD
  ZeroSumAccount:Transfers

2005-01-03 Transfer
  Assets:TB_Trading  20 USD
  ZeroSumAccount:Transfers
```
Doing so has a few advantages:

    a) on 2005-01-02, your assets are accurately represented:
    Bank_of_Ameriplus is short by $20, TB_Trading still doesn't have it, and
    the ZeroSumAccount:Transfers account captures that the money is still
    yours, but is "in flight."

    b) One can convert each bank's transactions directly into double-entry
    ledger statements. No need to remove the transaction from one of the
    banks. When you look at your journal files for each account, they match
    your account statements exactly.

    c) Import/conversion (from say, a bank .csv or .ofx) is easier, because
    your import scripts don't have to figure out where a transfer goes, and
    can simply assign transfers to  ZeroSumAccount:Transfers

    d) If there is a problem, your ZeroSumAccount:Transfers will sum to a
    non-zero value. Errors can therefore be found easily.


#### What this plugin does:

Account statements from institutions can be directly converted to double-entry
format, with transfers simply going to a special transfers account (eg:
Assets:ZeroSumAccount:Transfers).

In this plugin, we identify sets of postings in the specified ZeroSum accounts
that sum up to zero, and move them to a specified target account. This target
account will always sum up to zero and needs no further attention. The
postings remaining in the original ZeroSum accounts were the ones that could
not be matched, and potentially need attention.

The plugin operates on postings (not transactions) in the ZeroSum accounts.
This way, transactions with multiple postings to a ZeroSum account are still
matched without special handling.

The following examples will be matched and moved by this plugin:

    Example 1:
    ----------
    Input:
        2005-01-01 Transfer
          Assets:Bank_of_Ameriplus  -20 USD
          ZeroSumAccount:Transfers

        2005-01-03 Transfer
          Assets:TB_Trading  20 USD
          ZeroSumAccount:Transfers
    Output:
        2005-01-01 Transfer
          Assets:Bank_of_Ameriplus  -20 USD
          ZeroSumAccount-Matched:Transfers

        2005-01-03 Transfer
          Assets:TB_Trading  20 USD
          ZeroSumAccount-Matched:Transfers

    Example 2 (Only input shown):
    -----------------------------
    2005-01-01 Transfer
      Assets:Bank_of_Ameriplus  -20 USD
      ZeroSumAccount:Transfers   10 USD
      ZeroSumAccount:Transfers   10 USD

    2005-01-03 Transfer
      Assets:TB_Trading_A  10 USD
      ZeroSumAccount:Transfers

    2005-01-04 Transfer
      Assets:TB_Trading_B  10 USD
      ZeroSumAccount:Transfers

The following examples will NOT be matched:

    Example A:
    ----------
    2005-01-01 Transfer
      Assets:Bank_of_Ameriplus  -20 USD
      ZeroSumAccount:Transfers   10 USD
      ZeroSumAccount:Transfers   10 USD

    2005-01-03 Transfer
      Assets:TB_Trading  20 USD
      ZeroSumAccount:Transfers

    Example B:
    ----------
    2005-01-01 Transfer
      Assets:Bank_of_Ameriplus  -20 USD
      ZeroSumAccount:Transfers

    2005-01-03 Transfer
      Assets:TB_Trading_A  10 USD
      ZeroSumAccount:Transfers

    2005-01-03 Transfer
      Assets:TB_Trading_B  10 USD
      ZeroSumAccount:Transfers


The plugin does not append/remove the original set of input transaction
entries. It only changes the accounts to which postings are made. The plugin
also automatically adds "Open" directives for the target accounts to which
matched transactions are moved.

#### Invoking the plugin:

First, an example:

    plugin "beancount_plugins.plugins.zero_sum.zerosum" "{
     'zerosum_accounts' : {
     'Assets:Zero-Sum-Accounts:Bank-Account-Transfers' : ('Assets:ZSA-Matched:Bank-Account-Transfers', 30),
     'Assets:Zero-Sum-Accounts:Credit-Card-Payments'   : ('Assets:ZSA-Matched:Credit-Card-Payments'  ,  6),
     'Assets:Zero-Sum-Accounts:Temporary'              : ('Assets:ZSA-Matched:Temporary'             , 90),
      }
     }"

As the example shows, the argument is a dictionary where the keys are the set
of accounts on which the plugin should operate. The values are
(target_account, date_range), where the target_account is the account to which
the plugin should move matched postings, and the date_range is the range over
which to check for matches for that account.

## Split Transactions

```
plugin "beancount_plugins.plugins.split_transactions.split_transactions"
```
Documentation to come.
