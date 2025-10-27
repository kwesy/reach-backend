This documentation outlines the **Double-Entry Bookkeeping System** for the Reach fintech platform, covering deposits, withdrawals, internal transfers, and fee handling.

The system relies on the core principle of double-entry: **For every transaction, the total Debits (DR) must equal the total Credits (CR).**

-----

## Reach Platform Accounting Documentation

### 1\. Core Account Classifications

The system requires separating accounts into fundamental accounting roles. While you use internal names like "User Account" and "Platform Cash," these roles define how Debits and Credits affect the balance.

| Account Type | Simple Role | Increase By | Decrease By | Normal Balance | Example Accounts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Asset** | Money In Hand (Platform Cash) | **Debit (DR)** | Credit (CR) | Debit | Platform MoMo Cash (ID 100) |
| **Liability** | Money Owed (User Balances) | **Credit (CR)** | Debit (DR) | Credit | User A's Account (ID 1) |
| **Revenue** | Money Earned (Fees) | **Credit (CR)** | Debit (DR) | Credit | Fee Revenue (ID 3000) |
| **Expense** | Money Spent (Costs) | **Debit (DR)** | Credit (CR) | Debit | MoMo Transaction Expense (ID 4001) |

-----

### 2\. Standard Transaction Journal Entries

All entries are recorded in the $\text{Ledger}$ table, linked by a single $\text{AccountTransaction}$ ID.

#### A. Deposit (User to Platform)

**Scenario:** User A deposits $\text{GHS 50}$.

| Account ID | Account Name | Role | Entry Type | Amount (GHS) |
| :--- | :--- | :--- | :--- | :--- |
| **100** | Platform MoMo Cash | Asset | **Debit** | 50.00 |
| **1** | User A's Account | Liability | **Credit** | 50.00 |

\<hr\>

#### B. Internal User-to-User Transfer

**Scenario:** User A transfers $\text{GHS 50}$ to User B. (No platform cash movement).

| Account ID | Account Name | Role | Entry Type | Amount (GHS) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | User A's Account | Liability | **Debit** | 50.00 |
| **2** | User B's Account | Liability | **Credit** | 50.00 |

\<hr\>

#### C. Withdrawal with Fees (Standard Method - Separate Transactions)

This is the cleanest approach, breaking the event into two distinct transactions.

**Scenario:** User A withdraws $\text{GHS 50}$ net. User pays $\text{GHS 1}$ internal fee and $\text{GHS 2}$ external fee. **Total deduction: $\text{GHS 53}$**.

##### TXN-A: Principal Withdrawal and External Fee (Cash Movement)

| Account ID | Account Name | Role | Entry Type | Amount (GHS) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | User A's Account | Liability | **Debit** | 52.00 |
| **100** | Platform MoMo Cash | Asset | **Credit** | 52.00 |
*Rationale: Deducts principal + external fee from user's balance and reduces cash by the same amount.*

##### TXN-B: Internal Platform Fee (Revenue Recognition)

| Account ID | Account Name | Role | Entry Type | Amount (GHS) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | User A's Account | Liability | **Debit** | 1.00 |
| **3000** | Fee Revenue | Revenue | **Credit** | 1.00 |
*Rationale: Deducts the internal fee from user's balance and credits the platform's revenue.*

-----

### 3\. Balance Calculation

The final balance of any account is the cumulative sum of all ledger entries applied to it, respecting the Debit/Credit signs:

$$\text{Account Balance} = \sum (\text{Debits}) - \sum (\text{Credits})$$

For **Liability (User) Accounts**, the final balance is typically negative (Credit) when cash is owed. For reporting, the absolute value is displayed as the user's positive balance.

$$\text{User Balance} = \text{Absolute Value} (\sum \text{Credits} - \sum \text{Debits})$$

-----

### 4\. Accounting for Internal Fees (Critical Concept)

The internal fee is **always** credited to the **Revenue** account ($\text{3000}$) and **never** to the **Platform MoMo Cash (Asset)** account ($\text{100}$). This ensures the platform's earned income is correctly reported.

### 5\. Accounting for External Fees (Critical Concept)

  * **If the Platform Pays the External Fee:** The $\text{Expense}$ account ($\text{4001}$) must be **Debited** to show the cost, and the $\text{Platform MoMo Cash}$ ($\text{100}$) must be **Credited** for the full cash outflow.
  * **If the User Pays the External Fee:** The $\text{Expense}$ account is **not** used. The fee amount is simply part of the **Debit** to the user's $\text{Liability}$ account, as seen in $\text{TXN-010A}$ above.