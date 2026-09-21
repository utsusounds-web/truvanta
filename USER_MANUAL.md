# TRUVANTA — User Manual

**TRUVANTA is where you keep the record of your business** — what you sell,
what you have in stock, what people owe you, and how much money you're
really making. This manual explains every part of it in plain language.
You don't need any accounting or computer background to use it.

---

## 1. Getting started

### Creating your account
1. Open the app and tap **"Create account"**.
2. Fill in your name, email, a password, and a username (the username is
   just for signing in — you can pick anything, like your shop's name).
3. You'll then be asked to set up your **business** — its name, currency,
   and address. This only happens once.

### Signing in later
Just enter your email and password. You'll land straight back on your
dashboard with everything exactly as you left it.

> **If it ever asks you to "create a business" again after you already
> have one** — don't fill it in. Contact support instead; this means
> something went wrong; your data is still safe, it's just not showing you
> the right screen.

---

## 2. Your daily rhythm

Most days will look like this:

1. **Open a shift** (Shifts page) — count the cash in your drawer, enter
   it, and tap "Open shift." This is how the app knows a workday has
   started and can check your cash later.
2. **Sell things** (POS / Sell page) — add items to the cart, take payment,
   print or share the receipt.
3. **Close your shift** at the end of the day — count your cash again, the
   app tells you if it matches what it expects. If it doesn't, that's your
   signal to figure out why (an unrecorded expense, a mistake, etc.)
   *before* the discrepancy is forgotten.

Everything else — adding products, checking stock, following up on debts —
happens as needed around this daily rhythm.

---

## 3. Products & Inventory

### Adding a product
Go to **Products → Add product**. Fill in the name, price, and unit (e.g.
"piece," "kg," "carton"). A photo is optional but helps you find things
fast later, especially if you have many similar-looking items.

### Adding many products at once
If you're setting up for the first time and have a long list of goods,
use **Products → Bulk add** instead of adding them one by one. It opens a
table — fill in a row per product and save them all together.

### Recording stock coming in or going out
Go to **Inventory → Record movement**. Choose:
- **Stock Purchase** — you bought/received new stock (increases what you have)
- **Customer Return** — a customer gave something back (increases stock)
- **Damage / Expiry** — stock is no longer sellable (decreases stock)
- **Personal Use / Promotional Sample** — taken out for non-sale reasons (decreases stock)
- **Supplier Return** — you sent stock back to your supplier (decreases stock)
- **Stock Adjustment** — for correcting a count after a physical check

The app automatically adds or subtracts based on which reason you pick.

### Low stock warnings
Set a "reorder level" on each product. When stock drops to or below that
number, it shows up flagged on your Inventory page so you know to restock.

---

## 4. Selling (POS)

1. Search or tap products to add them to the cart.
2. Adjust quantities if needed.
3. Choose how the customer is paying — cash, bank transfer, card, or "on
   credit" (added to their account, see Customers below).
4. If a customer paid you in a **foreign currency** (e.g. USD), tick
   "Customer paid in a foreign currency," pick the currency, and enter what
   they handed over — the app converts it automatically using the rate you
   set in Settings.
5. Complete the sale. You can print the receipt or share it digitally.

**No internet?** The app keeps working — sales are saved on your device and
sent to the server automatically the next time you're online. Nothing is
lost.

---

## 5. Customers & credit

Add customers under **Customers**. When someone buys "on credit," it's
added to their running balance. You can see who owes you what at a glance,
and record payments as they pay you back under that customer's page.

---

## 6. Suppliers & Purchase Orders

Track who you buy from under **Suppliers**. Create a **Purchase Order**
when you're ordering new stock, then mark it "received" when it arrives —
this automatically adds the stock to your inventory and updates what you
owe that supplier.

*(This is one of the features that can be set to require a paid plan —
see "Billing" below. Whether it's free or paid depends on how the app
owner has configured it.)*

---

## 7. Expenses & money out

Record anything you spend — rent, transport, supplies — under **Expenses**.
This is what makes your profit numbers on the dashboard accurate: profit
isn't just "sales," it's sales minus everything that went out.

---

## 8. Staff & Roles

Invite staff under **Staff & Roles**. Each person gets a role (Owner,
Manager, Cashier, etc.) that controls what they can see and do — a cashier
can sell things but shouldn't be able to see your full financial reports or
change prices, for example.

---

## 9. Reports & Dashboard

The dashboard shows your sales, profit, and any warning signs at a glance.
Deeper reports (profitability per product, where your money is going) are
under **Reports**. You can export these as CSV files to open in Excel.

---

## 10. Owner Away Mode

If you're not physically at the shop, turn on **Away Mode** (Settings) and
set thresholds — e.g. "alert me if a discount over 10% is given" or "alert
me on any refund." You'll get a notification the moment something crosses
that line, even from far away.

---

## 11. Document Vault

Store important business documents (licenses, agreements, supplier
invoices) securely under **Documents**, instead of losing paper copies.

---

## 12. Your Profile & Security

Under **Profile**, you can update your name and photo, and see **every
device you're currently signed into**. If you lose your phone or suspect
someone else is using your account, sign that device out remotely from
this list — it's blocked immediately.

---

## 13. Billing (for the app owner/admin)

If you're the person running TRUVANTA as a business (renting it out to
other shop owners), **Platform Admin** is where you manage everything
about who pays for what:
- **Rent Mode** — the master ON/OFF switch. OFF means every feature is
  free for everyone, no matter what. ON means paid features require a
  subscription. You can flip this any time — for example, off during a
  free trial period, on once you're ready to charge.
- **Plans** — the pricing tiers you offer (e.g. Starter, Pro, Business),
  and which features each one unlocks.
- **Features** — the individual things that can be gated behind a plan.
- **Subscriptions** — see every business's current plan and payment status.
- **Overrides** — manually give or take away one specific feature for one
  specific business, regardless of their plan (for comps, trials, etc.)

---

## What's not finished yet — please read this

Being honest about where things stand:

- **AI features** (voice bookkeeping, receipt scanning) are not built yet
  — this needs a decision on which AI provider to use and its pricing
  before it can be built and correctly priced.
- **Hardware integrations** (dedicated receipt printers, barcode scanner
  hardware beyond what a browser/keyboard already supports) are not
  verified — this needs real devices to test against.
- **WhatsApp/Email notifications** are fully built but need real
  credentials entered in Settings → Platform Integrations before they'll
  actually send anything. Until then, notifications are recorded in the
  app but not delivered externally.
- Everything else described in this manual is complete and working.

---

## Getting help

If something looks broken or confusing, the two most useful things you can
send for help are: **what page you were on**, and **exactly what you did
right before it went wrong**. That's almost always enough to find and fix
the problem quickly.
