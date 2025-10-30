

# Accounts Types
| GL Code | Account Name                    | Type      | Notes                            |
| ------- | ------------------------------- | --------- | -------------------------------- |
| 1001    | Cash at Bank                    | Asset     | External settlement account      |
| 2001    | Customer Wallet Balances        | Liability | Sum of all user wallets          |
| 2002    | Suspense Account                | Liability | Temporary holding for mismatches |
| 5001    | Compensation Expense            | Expense   | Company-funded user credits      |
| 5002    | Operational Adjustments Expense | Expense   | System or write-off adjustments  |
| 4001    | Transaction Fees Income         | Revenue   | Income from user activity        |



# 💰 Fintech Transaction → Accounting Impact Table (with Arithmetic Operations)
| **Core Transaction**       | **Subtype / Use Case**             | **Debit Account (↑/↓)**        | **Credit Account (↑/↓)**       | **Effect Summary / Notes**                                          |
| -------------------------- | ---------------------------------- | ------------------------------ | ------------------------------ | ------------------------------------------------------------------- |
| **Deposit**                | Top-up (bank → wallet)        | **Cash at Bank ↑**             | **Customer Wallet Balances ↑** | User adds money; both company’s assets and liabilities increase.    |
| **Deposit**                | Compensation               | **Compensation Expense ↑**     | **Customer Wallet Balances ↑** | Fintech pays user from its own funds; expense recognized.           |
| **Withdrawal**             | Payout(cashout)                        | **Customer Wallet Balances ↓** | **Cash at Bank ↓**             | User withdraws funds; both liability and asset decrease.            |
| **Transfer**               | User A → User B                    | **User A Wallet ↓**            | **User B Wallet ↑**            | Internal movement; total liability unchanged.                       |
| **Adjustment (+)**         | Correction (increase user balance) | **Suspense ↓**                 | **Customer Wallet Balances ↑** | Fixing under-credit; suspense reduced or goes negative if unfunded. |
| **Adjustment (−)**         | Correction (reduce user balance)   | **Customer Wallet Balances ↓** | **Suspense ↑**                 | Fixing over-credit; suspense temporarily holds funds.               |
| **Adjustment (write-off)** | Irrecoverable balance              | **Operational Expense ↑**      | **Customer Wallet Balances ↓** | Writing off user debt or rounding differences; expense booked.      |



# Ledger Control Matrix for Fintechs (Crypto, Gift Cards, Digital Wallets)

This matrix shows:

- Which accounts to monitor  
- What normal vs abnormal balance states look like  
- What logic or alerts should trigger if something goes negative  
- What automatic actions or manual reviews should happen  

This design fits fintechs that deal in crypto, gift cards, and digital wallets, without lending.

---

## 🧭 1. Purpose of the Ledger Control Matrix

Your ledger control matrix acts like a **“watchdog”** that continuously validates:

💬 *“Does every user balance, asset account, and suspense account behave as it should?”*

It’s crucial for:

- Internal controls & reconciliation  
- Financial statement accuracy  
- Compliance with regulators (proof of funds, customer protection)  

---

## 💰 2. Ledger Control Matrix — Core Accounts

| Account / Ledger Type                  | Normal Balance Type | Allowed to Go Negative? | Alert Condition (Trigger)                                         | Control Logic / Action                                                                 | Frequency   |
|--------------------------------------|------------------|------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------|------------|
| User Wallet Balances (Liabilities)    | Credit (↑)       | ❌ No                  | Balance < 0                                                      | 🔸 Auto-block further debits<br>🔸 Trigger “Negative Wallet Alert”<br>🔸 Flag for finance/admin review | Real-time  |
| Cash at Bank (Asset)                  | Debit (↑)        | ⚠️ Yes, temporarily   | Balance < 0 for > 1 hour                                         | 🔸 Trigger “Negative Cash Alert”<br>🔸 Check for pending settlement delays or payout batch mismatch | Hourly     |
| Crypto Inventory (Asset)              | Debit (↑)        | ❌ No                  | Quantity < 0                                                     | 🔸 Block further sell trades<br>🔸 Trigger “Negative Inventory Alert”<br>🔸 Investigate trade reconciliation | Real-time  |
| Gift Card Inventory (Asset)           | Debit (↑)        | ❌ No                  | Quantity or value < 0                                            | 🔸 Stop sale transactions<br>🔸 Investigate stock reconciliation                         | Real-time  |
| Suspense Account (Liability / Temporary) | Credit (↑)     | ✅ Yes, temporarily   | Debit balance > threshold (e.g., $500 or 0.1% of total liabilities) | 🔸 Flag “Negative Suspense Alert”<br>🔸 Auto-report to finance for clearing              | Daily      |
| Compensation Expense (Expense)        | Debit (↑)        | ✅ Yes                 | N/A                                                              | Normal expense growth                                                                  | N/A        |
| Revenue (Income)                      | Credit (↑)       | ⚠️ Yes, but only for refunds | Net negative revenue                                           | 🔸 Review refund logic<br>🔸 Investigate potential reversals or chargebacks             | Daily      |
| System Control Account (P&L clearing) | Credit/Debit    | ❌ No persistent balance | Non-zero at end of day                                          | 🔸 Auto-clear via daily journal<br>🔸 Alert if residual balance remains                  | Daily      |

---

## 🧩 3. Example Automated Control Logic (Pseudocode)

Here’s how you could implement the logic in your ledger microservice or reconciliation job:

```python
# Run hourly or in real-time
for account in all_accounts:
    balance = get_balance(account)

    if account.type == "UserWallet" and balance < 0:
        alert("NEGATIVE USER BALANCE", account.id, balance)
        freeze_account(account.id)

    elif account.type == "CashAtBank" and balance < 0:
        alert("NEGATIVE CASH BALANCE", account.id, balance)

    elif account.type in ["CryptoInventory", "GiftCardInventory"] and balance < 0:
        alert("NEGATIVE INVENTORY", account.id, balance)
        block_sales(account.id)

    elif account.type == "Suspense" and balance < -threshold:
        alert("NEGATIVE SUSPENSE BALANCE", account.id, balance)
        notify_finance_team(account.id)

    elif account.type == "SystemControl" and abs(balance) > tolerance:
        alert("UNCLEARED SYSTEM CONTROL BALANCE", account.id, balance)
```
---

## 🧾 4. Recommended Alert Severity Levels

| Severity | Example Trigger                              | Action                                             |
|---------|---------------------------------------------|--------------------------------------------------|
| 🟥 Critical | User wallet < 0, or crypto inventory < 0   | Block transactions immediately; escalate to ops/finance |
| 🟧 High    | Suspense negative > threshold              | Escalate to finance for journal clearing        |
| 🟨 Medium  | Cash at bank temporarily negative          | Monitor, no user impact yet                     |
| 🟩 Low     | Small rounding or pending batch            | Auto-clear or ignore if within tolerance       |

---

## ⚙️ 5. Optional Dashboards

For better operational control, build a **Ledger Health Dashboard** that shows:

| Metric                        | Target                                         | Example Display   |
|-------------------------------|-----------------------------------------------|-----------------|
| Total User Wallets             | = Total Cash + Crypto + Gift Cards ± Suspense | ✅ Balanced      |
| Suspense Account Balance       | 0 (tolerance ±$50)                            | ⚠️ $25 pending   |
| # of Negative User Wallets     | 0                                             | 🟢 0 found       |
| # of Negative Suspense Accounts | 0                                           | 🟢 0 found       |
| Crypto Inventory Quantity      | ≥ 0                                           | ✅ 1.25 BTC      |
| Gift Card Stock                | ≥ 0                                           | ✅ 215 units     |

---

## ✅ 6. Summary — Who Can Go Negative and Control Response

| Account Type          | Allowed Negative? | Response                                |
|----------------------|-----------------|----------------------------------------|
| User Wallet          | ❌ Never         | Block debit + alert immediately         |
| Cash at Bank         | ⚠️ Temporary     | Monitor; clear via reconciliation      |
| Crypto Inventory     | ❌ Never         | Block trade + alert                     |
| Gift Card Inventory  | ❌ Never         | Block trade + alert                     |
| Suspense             | ✅ Temporary     | Clear daily; alert if persistent       |
| Expense / Revenue    | ✅ Normal        | No system restriction                   |
