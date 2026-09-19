---
stimulus_id: ltv_001_ai_scaffolding__reworded_1
unit_id: ltv_001
condition: ai_scaffolding
variant: reworded_1
---
# Explanation

Let's figure out customer lifetime value together. It asks how much one customer is worth to a business across the whole relationship, not just at the first sale. It is the number that sets how much a company can afford to spend on winning customers, and it turns a marketing budget from a cost into an investment that earns a return. It is built from two pieces: what the company keeps from a customer each period, and how many periods that customer sticks around.

The first piece is a margin, not a price. A EUR 50 subscription that costs EUR 20 to serve leaves EUR 30, and only that EUR 30 can pay for acquisition, overheads and profit. The second piece comes from churn: when a steady share of customers leaves every month, the average customer stays one divided by that share, so 4% monthly churn means an average life of 25 months and 2% means 50 months.

Put the two pieces together:

Lifetime value = Monthly revenue x Gross margin / Monthly churn rate

Worked example. A gym charges EUR 40 a month. Staff, cleaning and equipment wear eat up 30% of that, leaving a 70% gross margin, and 7% of members cancel every month. Margin per member per month = 40 x 0.7 = EUR 28. The average member stays 1 / 0.07 months. Lifetime value = 28 / 0.07 = EUR 400.

The slip is building the whole thing on revenue rather than margin. For the gym that gives 40 / 0.07 = EUR 571, which would justify spending far more on new members than the club can afford, since the cost of serving them was never subtracted. A second form of the same slip assumes every customer stays exactly a year, ignoring what the churn rate says: at 7% a month the average member stays well over a year, and better retention is worth as much as a higher price. Hold on to that while you tackle the problem below, because if your result is off, I will start by asking what you did with the gross margin.

# Problem

A software company charges EUR 60 per customer per month. Its gross margin is 75% of that revenue, and 5% of its customers cancel each month. What is the lifetime value of a customer, before discounting? Have a go on your own first. I won't give you the answer: if you get it wrong, I'll ask you something about how you worked it out and offer a hint, and then you can try again.

# Diagnostic questions

Before I comment on your result, here are three questions for you.

Out of the EUR 60 a customer pays every month, how much does this company really keep?

If 5% of customers cancel each month, how long does a customer stay, and how did you get that from the churn rate?

Imagine someone divides 60 by 0.05 and reports that. Which cost did they forget to take out?

# Hints

Hint 1: Lifetime value has two parts: what the company keeps from a customer every month, and how many months the customer stays. Work out each before you combine them.

Hint 2: The company does not keep the full subscription fee. Apply the gross margin to the monthly revenue first, so the cost of serving the customer is already removed.

Hint 3: A monthly cancellation rate means an average life of one divided by that rate. Dividing the monthly margin by the churn rate does the same thing in one step.

The last step of the calculation is for you to do.
