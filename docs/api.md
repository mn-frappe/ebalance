# API Reference

## Whitelisted Methods

### Financial Reports

#### `ebalance.api.submit_balance_sheet`

Submit balance sheet to MOF.

```python
import frappe

result = frappe.call(
    "ebalance.api.submit_balance_sheet",
    fiscal_year="2024",
    period="Q4"
)
```

---

#### `ebalance.api.submit_income_statement`

Submit income statement to MOF.

```python
result = frappe.call(
    "ebalance.api.submit_income_statement",
    fiscal_year="2024",
    period="Q4"
)
```

---

#### `ebalance.api.get_submission_status`

Check submission status.

```python
result = frappe.call(
    "ebalance.api.get_submission_status",
    submission_id="sub_123"
)
```

## JavaScript API

```javascript
frappe.call({
    method: "ebalance.api.submit_balance_sheet",
    args: {
        fiscal_year: "2024",
        period: "Q4"
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```
