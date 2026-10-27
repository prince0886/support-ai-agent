"""Sample knowledge base and demo tickets for Northwind Supply Co.

Everything here is fictional demo content. The knowledge articles are the only
source of truth the analysis engine is allowed to quote, which is what keeps the
generated replies grounded.
"""

from __future__ import annotations

from .domain import Category

COMPANY_NAME = "Northwind Supply Co."

KNOWLEDGE_ARTICLES: list[dict] = [
    {
        "slug": "shipping-times-and-tracking",
        "title": "Shipping times, carriers and tracking",
        "category": Category.SHIPPING.value,
        "article_type": "policy",
        "summary": "Standard and express delivery windows, dispatch cut-off, and when tracking updates.",
        "tags": ["shipping", "delivery", "tracking", "express", "standard", "dispatch"],
        "content": (
            "Standard shipping arrives within 3 to 5 business days after dispatch, while express shipping "
            "arrives within 1 to 2 business days. Orders placed before 2:00 PM local time on a business day "
            "are dispatched the same day, and orders placed later are dispatched the next business day.\n"
            "A tracking number is emailed as soon as the carrier scans the parcel, which can take up to 24 hours "
            "after dispatch. Tracking pages sometimes show 'label created' until the parcel reaches the first "
            "carrier hub, so a tracking page that has not updated for 24 to 48 hours is usually not lost.\n"
            "We ship with UPS, FedEx and DHL depending on destination. Weekend and public holiday orders are "
            "dispatched on the next business day."
        ),
    },
    {
        "slug": "shipping-delays",
        "title": "What to do when a shipment is delayed",
        "category": Category.SHIPPING.value,
        "article_type": "guide",
        "summary": "Carrier delays, how long to wait, and what support can and cannot confirm.",
        "tags": ["delayed", "late", "shipping", "delivery", "tracking", "stuck"],
        "content": (
            "Carrier delays of 1 to 3 business days are common during peak periods, severe weather and customs "
            "processing, and the parcel usually continues moving without any action from the customer.\n"
            "If tracking has not updated for more than 5 business days past the estimated delivery date, we can "
            "open a carrier investigation. An investigation takes 2 to 5 business days and the carrier will "
            "contact the recipient directly if it needs more information.\n"
            "Support agents cannot promise a specific delivery date or upgrade a parcel that is already in "
            "transit, and expedited shipping fees are not refunded because a carrier is running late. If a "
            "delivery date is critical, the safest option is to place a second order with express shipping and "
            "return the delayed parcel once it arrives, provided it is still within the return window."
        ),
    },
    {
        "slug": "lost-or-missing-package",
        "title": "Package marked delivered but not received",
        "category": Category.SHIPPING.value,
        "article_type": "policy",
        "summary": "Steps for a missing parcel, carrier claims and replacement eligibility.",
        "tags": ["missing", "lost", "delivered", "stolen", "package", "carrier claim"],
        "content": (
            "When tracking shows a parcel as delivered but it has not arrived, we ask the customer to check "
            "around the property, with neighbours and with the building reception, and to wait 24 hours because "
            "carriers occasionally scan parcels before the final drop.\n"
            "If the parcel is still missing after 24 hours, support opens a carrier claim. Claims take 3 to 5 "
            "business days to resolve, and a replacement or refund is only issued after the carrier confirms the "
            "parcel is lost. Support cannot approve a replacement on the first contact.\n"
            "Parcels reported as stolen after a confirmed delivery are reviewed case by case, and a police "
            "report reference helps the review."
        ),
    },
    {
        "slug": "damaged-or-wrong-item",
        "title": "Damaged, defective or incorrect item",
        "category": Category.SHIPPING.value,
        "article_type": "policy",
        "summary": "How to report damage or a wrong item and what happens next.",
        "tags": ["damaged", "broken", "defective", "wrong item", "replacement", "photo"],
        "content": (
            "Report damage or an incorrect item within 48 hours of delivery and include photos of the item, the "
            "packaging and the shipping label. Please keep the original packaging until the case is closed.\n"
            "Once the photos are received, our team reviews the case within 1 business day and confirms whether "
            "a replacement or a refund applies. Defective items are replaced at no cost and the return label is "
            "covered by us.\n"
            "Support cannot confirm a replacement or refund before the review is complete, so agents should not "
            "promise an outcome on the first reply."
        ),
    },
    {
        "slug": "international-shipping",
        "title": "International shipping, duties and delivery times",
        "category": Category.SHIPPING.value,
        "article_type": "faq",
        "summary": "Which countries we ship to, delivery windows, customs and PO box limits.",
        "tags": ["international", "japan", "canada", "europe", "customs", "duties", "delivery"],
        "content": (
            "We ship to more than 40 countries, including Japan, Canada, the United Kingdom, Australia and the "
            "European Union. International parcels are sent with DHL Express and arrive within 5 to 10 business "
            "days after dispatch.\n"
            "Import duties and taxes are calculated at checkout for most destinations. Where they are not "
            "prepaid, the recipient is responsible for paying them on delivery.\n"
            "International orders cannot be delivered to PO boxes, and express shipping is the only available "
            "option outside the United States."
        ),
    },
    {
        "slug": "shipping-address-changes",
        "title": "Changing a shipping address after ordering",
        "category": Category.SHIPPING.value,
        "article_type": "faq",
        "summary": "Whether an address can be changed and what happens if a parcel is returned to sender.",
        "tags": ["address", "change", "shipping", "return to sender"],
        "content": (
            "A shipping address can be changed only while an order is still in the 'processing' state. Once the "
            "parcel is dispatched the address is locked by the carrier and cannot be edited by support.\n"
            "If a parcel is returned to sender because an address was incomplete or incorrect, it is checked in "
            "at our warehouse within 5 business days and the order is refunded minus the original shipping fee "
            "once the check-in is complete."
        ),
    },
    {
        "slug": "refund-policy",
        "title": "30-day refund policy",
        "category": Category.REFUND.value,
        "article_type": "policy",
        "summary": "Eligibility window, item condition, refund method and non-refundable fees.",
        "tags": ["refund", "return", "30 days", "policy", "eligibility", "shipping fee"],
        "content": (
            "Unused items in their original packaging can be returned within 30 days of delivery for a refund to "
            "the original payment method. Items must be unused, with all accessories and labels included, and "
            "the return must be shipped within 14 days of the return being approved.\n"
            "Refunds are issued after the returned item passes inspection at our warehouse. Original shipping "
            "fees are non-refundable unless the item was defective or the wrong item was sent.\n"
            "Final-sale and clearance items are not eligible for a refund. Digital gift cards and downloadable "
            "software are non-refundable once the code has been redeemed."
        ),
    },
    {
        "slug": "how-to-start-a-return",
        "title": "How to start a return",
        "category": Category.REFUND.value,
        "article_type": "guide",
        "summary": "Step-by-step return request, label and drop-off instructions.",
        "tags": ["return", "label", "rma", "drop off", "how to", "refund"],
        "content": (
            "To start a return, open Account, then Orders, select the order and choose 'Return or exchange'. "
            "Pick the items and a reason, and the return authorisation is generated immediately for eligible "
            "orders.\n"
            "A prepaid return label is emailed within a few minutes of the request. Drop the parcel at any "
            "carrier access point within 14 days. Keep the drop-off receipt until the refund is confirmed.\n"
            "If the order does not show a return option, the 30-day window has likely closed and the request "
            "needs a manual review by a support agent."
        ),
    },
    {
        "slug": "refund-timeline",
        "title": "When will my refund arrive?",
        "category": Category.REFUND.value,
        "article_type": "faq",
        "summary": "Inspection and banking timelines for refunds, and how to check status.",
        "tags": ["refund", "timeline", "status", "pending", "bank", "when"],
        "content": (
            "Once a returned parcel reaches our warehouse it is inspected within 2 business days. After "
            "inspection, the refund is issued to the original payment method and typically appears within 5 to "
            "10 business days, depending on the bank or card issuer.\n"
            "The refund confirmation email includes a refund reference that can be shared with the bank if the "
            "credit has not appeared after 10 business days.\n"
            "Support can look up the status of a specific refund when the customer provides the order number and "
            "the email address used at checkout. Agents should not estimate a refund date for a parcel that has "
            "not yet been checked in."
        ),
    },
    {
        "slug": "refund-exceptions",
        "title": "Exceptions to the standard refund policy",
        "category": Category.REFUND.value,
        "article_type": "policy",
        "summary": "Late-window requests, high-value orders and who can approve an exception.",
        "tags": ["exception", "policy", "late", "supervisor", "approval", "goodwill"],
        "content": (
            "Requests made after the 30-day window are reviewed case by case. They are never approved "
            "automatically, and only a support supervisor can approve an exception as a goodwill gesture.\n"
            "Exceptions for orders above 250 USD require supervisor approval and a documented reason. Items "
            "marked final sale, clearance, personal care or custom-made are excluded from exceptions.\n"
            "Support agents should acknowledge the request, explain the standard policy and escalate to a "
            "supervisor without promising an outcome."
        ),
    },
    {
        "slug": "warranty-and-replacements",
        "title": "Warranty claims and replacements",
        "category": Category.REFUND.value,
        "article_type": "policy",
        "summary": "12-month manufacturing warranty, proof of purchase and replacement process.",
        "tags": ["warranty", "replacement", "defect", "12 months", "claim"],
        "content": (
            "Northwind products carry a 12-month warranty against manufacturing defects, starting on the "
            "delivery date. The warranty covers defects in materials and workmanship and does not cover normal "
            "wear, accidental damage or misuse.\n"
            "To file a claim, send the order number, a description of the fault and photos or a short video. "
            "Approved claims are handled with a replacement where stock allows, and refunds apply only when a "
            "replacement is unavailable."
        ),
    },
    {
        "slug": "failed-payments",
        "title": "Why a card payment may fail",
        "category": Category.BILLING.value,
        "article_type": "guide",
        "summary": "Common decline reasons, pending authorisations and safe retry guidance.",
        "tags": ["payment", "declined", "failed", "card", "authorization", "pending", "checkout"],
        "content": (
            "Card payments are usually declined because the bank blocked the transaction, the billing address "
            "did not match, 3-D Secure verification was not completed, or the available balance was too low at "
            "the moment of purchase.\n"
            "A failed payment can still create a temporary authorisation hold at the bank. Holds are released "
            "automatically within 3 to 5 business days and are not a completed charge. A customer who sees a "
            "pending amount after a declined payment should not retry repeatedly, because each attempt can "
            "create another hold.\n"
            "Support can confirm whether an order was paid, but cannot remove a bank hold or approve a payment. "
            "Alternative payment methods are PayPal, Apple Pay and Google Pay."
        ),
    },
    {
        "slug": "duplicate-charges",
        "title": "Duplicate or unexpected charges",
        "category": Category.BILLING.value,
        "article_type": "policy",
        "summary": "How duplicate charges are reviewed, reversed and communicated.",
        "tags": ["duplicate", "double charged", "charge", "refund", "billing", "bank"],
        "content": (
            "If a customer sees two completed charges for one order, support collects the order number, the last "
            "four digits of the card and the charge dates, then forwards the case to the billing team.\n"
            "The billing team verifies the charges within 1 to 2 business days. Confirmed duplicates are "
            "reversed to the original payment method, which can take a further 5 to 10 business days to appear "
            "on the statement.\n"
            "A pending authorisation that matches the order total is not a duplicate charge and should not be "
            "treated as one until it settles."
        ),
    },
    {
        "slug": "subscription-billing",
        "title": "Subscription renewals and invoices",
        "category": Category.BILLING.value,
        "article_type": "faq",
        "summary": "Renewal dates, cancellation timing, receipts and plan changes.",
        "tags": ["subscription", "renewal", "invoice", "receipt", "cancel", "plan"],
        "content": (
            "Subscriptions renew automatically every month or year on the date of the original purchase. The "
            "renewal date and amount are shown under Account, then Billing, before the charge is taken.\n"
            "A subscription can be cancelled at any time before the renewal date. Cancellation stops future "
            "charges but does not refund the current period, and access continues until the end of the paid "
            "period.\n"
            "Paid invoices are available under Account, then Billing, then Invoices, and can be downloaded as a "
            "PDF for expense reports."
        ),
    },
    {
        "slug": "payment-methods",
        "title": "Accepted payment methods and currencies",
        "category": Category.BILLING.value,
        "article_type": "faq",
        "summary": "Cards and wallets accepted, currency handling and billing descriptors.",
        "tags": ["payment", "methods", "paypal", "apple pay", "currency", "descriptor"],
        "content": (
            "We accept Visa, Mastercard, American Express, PayPal, Apple Pay and Google Pay. Cash on delivery and "
            "bank transfers are not available.\n"
            "All orders are charged in USD. If the card is issued outside the United States, the bank applies its "
            "own conversion rate and may add a foreign transaction fee.\n"
            "Charges appear on statements as NORTHWIND SUPPLY."
        ),
    },
    {
        "slug": "sign-in-help",
        "title": "Can't sign in: password and account access",
        "category": Category.TECHNICAL.value,
        "article_type": "guide",
        "summary": "Password reset steps, lockout rules and what to do when a reset email never arrives.",
        "tags": ["login", "sign in", "password", "reset", "locked", "access", "email"],
        "content": (
            "Use 'Forgot password' on the sign-in screen to receive a reset link. Reset links expire after 30 "
            "minutes and can only be used once, so a link that has expired needs to be requested again.\n"
            "If the email does not arrive within 10 minutes, check the spam and promotions folders and confirm "
            "that the address matches the account. Accounts are temporarily locked for 15 minutes after five "
            "failed sign-in attempts, and the lock clears automatically.\n"
            "Support cannot reset a password or change the email on an account without identity verification. "
            "Suspicious sign-in activity is escalated to the security team."
        ),
    },
    {
        "slug": "app-troubleshooting",
        "title": "App crashing, spinning or showing an error",
        "category": Category.TECHNICAL.value,
        "article_type": "guide",
        "summary": "Basic troubleshooting steps, supported browsers and what to send engineering.",
        "tags": ["error", "crash", "dashboard", "spinning", "bug", "500", "cache", "browser"],
        "content": (
            "First update the app or refresh the browser, then sign out and back in. Clearing the browser cache "
            "or the app cache resolves most loading and rendering problems on the dashboard.\n"
            "We support the latest two versions of Chrome, Safari, Edge and Firefox. Very old browser versions "
            "and aggressive content blockers can stop the dashboard from loading.\n"
            "If the problem persists, send the error code shown on screen, the browser or app version, the "
            "account email and a screenshot. Errors beginning with ERR-500 are server-side and are escalated to "
            "engineering, where the target first response is 1 business day."
        ),
    },
    {
        "slug": "two-factor-authentication",
        "title": "Two-factor authentication help",
        "category": Category.TECHNICAL.value,
        "article_type": "guide",
        "summary": "Missing codes, device time sync, backup codes and recovery.",
        "tags": ["2fa", "two factor", "code", "authenticator", "backup", "verification"],
        "content": (
            "If a one-time code does not arrive, wait for the current code to expire and request a new one. "
            "Authenticator codes are time-based, so the phone clock must be set to automatic time.\n"
            "Backup codes were shown when two-factor authentication was enabled and each code can be used once. "
            "If the authenticator device is lost and no backup codes remain, support starts an identity "
            "verification flow before two-factor authentication can be reset."
        ),
    },
    {
        "slug": "support-hours",
        "title": "Support hours and response times",
        "category": Category.GENERAL.value,
        "article_type": "faq",
        "summary": "When the team is online, expected first response and urgent contact paths.",
        "tags": ["hours", "support", "contact", "response time", "weekend"],
        "content": (
            "The support team is available Monday to Friday, 9:00 AM to 6:00 PM Eastern Time. Messages received "
            "outside those hours are answered on the next business day.\n"
            "The target first response is within 1 business day for email and within 2 hours during support hours "
            "for live chat. Urgent account or payment issues are prioritised in the queue."
        ),
    },
    {
        "slug": "account-details",
        "title": "Update your email, name or account details",
        "category": Category.GENERAL.value,
        "article_type": "faq",
        "summary": "Self-service profile changes, email verification and password updates.",
        "tags": ["email", "address", "profile", "name", "account", "update", "password"],
        "content": (
            "Email address, name, phone number and default shipping address can be updated under Account, then "
            "Profile. A change of email address requires confirmation from both the old and the new address.\n"
            "Changes to an email address usually take effect immediately, while pending orders keep the contact "
            "details used at checkout."
        ),
    },
]


DEMO_TICKETS: list[dict] = [
    {
        "customer_name": "Maya Chen",
        "customer_email": "maya.chen@example.com",
        "subject": "Order NW-48213 still hasn't shipped",
        "message": (
            "Hi, I ordered a camping stove six days ago with standard shipping and tracking has been stuck on "
            "'label created' since Tuesday. We leave for a trip on Friday and I really need it before then. Can "
            "you check what's happening with order NW-48213?"
        ),
        "channel": "email",
        "status": "new",
        "hours_ago": 2,
    },
    {
        "customer_name": "Daniel Okafor",
        "customer_email": "daniel.okafor@example.com",
        "subject": "Refund for unopened Ridgeline 4P tent",
        "message": (
            "I bought the Ridgeline 4P tent last week (order NW-47118) but we ended up using a friend's tent. "
            "It's still sealed in the original box. Can I return it for a refund? Happy to ship it back."
        ),
        "channel": "email",
        "status": "new",
        "hours_ago": 5,
    },
    {
        "customer_name": "Priya Raman",
        "customer_email": "priya.raman@example.com",
        "subject": "Payment declined but money is missing from my account",
        "message": (
            "I tried to renew my subscription today. The checkout said my card was declined, but my bank app "
            "shows a pending charge of $89 from Northwind. I do not want to be charged twice and I need this "
            "cleared up today."
        ),
        "channel": "chat",
        "status": "new",
        "hours_ago": 1,
    },
    {
        "customer_name": "Tom Becker",
        "customer_email": "tom.becker@example.com",
        "subject": "Dashboard stuck on ERR-500 after update",
        "message": (
            "Since your latest update the dashboard just spins and then shows 'Something went wrong (ERR-500)'. "
            "I've tried Chrome, Edge and the mobile app, and cleared the cache twice. I manage 12 team accounts "
            "and we're completely blocked. This is urgent."
        ),
        "channel": "chat",
        "status": "in_progress",
        "hours_ago": 26,
        "conversation": [
            {
                "role": "assistant",
                "author": "Agent Rhea",
                "hours_after": 1,
                "body": (
                    "Hi Tom, thanks for flagging this and sorry for the disruption. ERR-500 is a server-side "
                    "error, so I've passed it to engineering with your account details and the browsers you "
                    "tested. Target first response from engineering is within 1 business day, and I'll update "
                    "you here as soon as I have news. Thanks for your patience."
                ),
            }
        ],
    },
    {
        "customer_name": "Angela Torres",
        "customer_email": "angela.torres@example.com",
        "subject": "Refusing my refund over 9 days is unacceptable",
        "message": (
            "I've been a customer for four years and you're seriously refusing to refund a $340 jacket because "
            "I'm 9 days past your 30-day window? The jacket is unworn with tags. This is ridiculous. Make an "
            "exception or I'm disputing the charge with my bank and posting about this everywhere."
        ),
        "channel": "email",
        "status": "escalated",
        "hours_ago": 30,
        "escalation_reason": (
            "Policy exception requested: the return is 9 days past the 30-day window and only a supervisor can "
            "approve goodwill. The message also includes a chargeback and public-review threat."
        ),
    },
    {
        "customer_name": "Sam Whitfield",
        "customer_email": "sam.whitfield@example.com",
        "subject": "Espresso machine marked delivered, nothing here",
        "message": (
            "Tracking says my espresso machine was delivered yesterday at 2:14 PM but nothing arrived. I checked "
            "with both neighbours and the building reception. It was $210. What happens now?"
        ),
        "channel": "email",
        "status": "new",
        "hours_ago": 8,
    },
    {
        "customer_name": "Lena Hoffmann",
        "customer_email": "lena.hoffmann@example.com",
        "subject": "How do I change the email on my account?",
        "message": (
            "Hello, my old work email is still on my account and I'd like to switch to my personal address. "
            "Where do I update it?"
        ),
        "channel": "email",
        "status": "resolved",
        "hours_ago": 52,
        "conversation": [
            {
                "role": "assistant",
                "author": "Agent Rhea",
                "hours_after": 1,
                "body": (
                    "Hi Lena, you can update it under Account, then Profile. A change of email needs confirmation "
                    "from both your old and new address, and it takes effect immediately. Pending orders keep the "
                    "contact details used at checkout. Let us know if the confirmation email doesn't arrive!"
                ),
            }
        ],
    },
    {
        "customer_name": "Marcus Field",
        "customer_email": "marcus.field@example.com",
        "subject": "Need a PDF invoice for February",
        "message": (
            "Could you send me a PDF invoice for my February subscription payment? Finance needs it for expense "
            "reporting."
        ),
        "channel": "email",
        "status": "resolved",
        "hours_ago": 70,
        "conversation": [
            {
                "role": "assistant",
                "author": "Agent Rhea",
                "hours_after": 2,
                "body": (
                    "Hi Marcus, paid invoices are available under Account, then Billing, then Invoices, where you "
                    "can download each one as a PDF. If February isn't listed, reply here and we'll pull it for "
                    "you."
                ),
            }
        ],
    },
    {
        "customer_name": "Aiko Tanaka",
        "customer_email": "aiko.tanaka@example.com",
        "subject": "Do you ship to Japan?",
        "message": (
            "Quick question before I order: do you ship to Japan, and roughly how long does delivery take? "
            "Thanks!"
        ),
        "channel": "email",
        "status": "new",
        "hours_ago": 14,
    },
]