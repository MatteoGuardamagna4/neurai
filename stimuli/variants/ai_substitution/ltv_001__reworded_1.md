---
stimulus_id: ltv_001_ai_substitution__reworded_1
unit_id: ltv_001
condition: ai_substitution
variant: reworded_1
---
# Explanation

Let's go through customer lifetime value together. It asks how much one customer is worth to a business across the whole relationship, not just at the first sale. It is the number that sets how much a company can afford to spend on winning customers, and it turns a marketing budget from a cost into an investment that earns a return. It is built from two pieces: what the company keeps from a customer each period, and how many periods that customer sticks around.

The first piece is a margin, not a price. A EUR 50 subscription that costs EUR 20 to serve leaves EUR 30, and only that EUR 30 can pay for acquisition, overheads and profit. The second piece comes from churn: when a steady share of customers leaves every month, the average customer stays one divided by that share, so 4% monthly churn means an average life of 25 months and 2% means 50 months.

Put the two pieces together:

Lifetime value = Monthly revenue x Gross margin / Monthly churn rate

Worked example. A gym charges EUR 40 a month. Staff, cleaning and equipment wear eat up 30% of that, leaving a 70% gross margin, and 7% of members cancel every month. Margin per member per month = 40 x 0.7 = EUR 28. The average member stays 1 / 0.07 months. Lifetime value = 28 / 0.07 = EUR 400.

The slip is building the whole thing on revenue rather than margin. For the gym that gives 40 / 0.07 = EUR 571, which would justify spending far more on new members than the club can afford, since the cost of serving them was never subtracted. A second form of the same slip assumes every customer stays exactly a year, ignoring what the churn rate says: at 7% a month the average member stays well over a year, and better retention is worth as much as a higher price. Keep that in mind as I walk you through the calculation below, because applying the gross margin is the step people skip most.

# Problem

A software company charges EUR 60 per customer per month. Its gross margin is 75% of that revenue, and 5% of its customers cancel each month. What is the lifetime value of a customer, before discounting? There is no need to work it out yourself. If you answer wrongly, I will show you the full calculation and the answer straight away, one step at a time.

# Worked solution

Step 1: find the monthly gross margin per customer: 60 x 0.75 = EUR 45. That is what the company keeps once the customer has been served. Step 2: find how long a customer lasts: if 5% cancel each month, the average customer stays 1 / 0.05 = 20 months. Step 3: multiply: 45 x 20 = EUR 900, the same as dividing the monthly margin by the churn rate. Using the full EUR 60 of revenue would give EUR 1,200, crediting the customer with money that actually goes on serving them. See how much more the answer reacts to churn than to price: halve the churn rate and lifetime value doubles, while a tenth more on the price moves it by only a tenth.

Use this method for the rest of the unit: multiply the period's revenue by the gross margin to get what the company keeps, then divide by the churn rate for that same period. If a question gives an average life in periods rather than a churn rate, multiply by that life instead of dividing. You don't need to work it out again; just follow the steps as shown.
