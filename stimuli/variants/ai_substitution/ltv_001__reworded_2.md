---
stimulus_id: ltv_001_ai_substitution__reworded_2
unit_id: ltv_001
condition: ai_substitution
variant: reworded_2
---
# Explanation

Let us examine customer lifetime value together. It addresses the worth of an individual customer to a business over the entire relationship, rather than at the point of the first sale. It is the figure that determines how much a company can afford to spend on acquiring customers, and it converts a marketing budget from a cost into an investment yielding a return. It is constructed from two elements: the amount the company retains from a customer in each period, and the number of periods for which that customer remains.

The first element is a margin, not a price. A subscription of EUR 50 that costs EUR 20 to serve leaves EUR 30, and only that EUR 30 is available for acquisition, overheads and profit. The second element derives from churn: where a constant proportion of customers departs each month, the average customer remains for one divided by that proportion, so a monthly churn of 4% implies an average life of 25 months and 2% implies 50 months.

Combining the two elements:

Lifetime value = Monthly revenue x Gross margin / Monthly churn rate

Worked example. A gym charges EUR 40 per month. Staffing, cleaning and equipment wear absorb 30% of that amount, leaving a 70% gross margin, and 7% of members cancel each month. Margin per member per month = 40 x 0.7 = EUR 28. The average member remains for 1 / 0.07 months. Lifetime value = 28 / 0.07 = EUR 400.

The characteristic error is to base the calculation on revenue rather than margin. For the gym this yields 40 / 0.07 = EUR 571, which would justify expenditure on new members well beyond what the club can sustain, since the cost of serving them has not been deducted. A related error assumes a fixed life of one year, disregarding the information conveyed by the churn rate: at 7% per month the average member remains well over a year, and improved retention is worth as much as a higher price. Bear this in mind as I present the calculation below, since the application of the gross margin is the step most commonly omitted.

# Problem

A software company charges EUR 60 per customer per month. Its gross margin is 75% of that revenue, and 5% of its customers cancel each month. What is the lifetime value of a customer, before discounting? It is not necessary to solve this yourself. Should your answer be incorrect, I shall present the complete calculation and the answer immediately, step by step.

# Worked solution

Step 1: determine the monthly gross margin per customer: 60 x 0.75 = EUR 45. This is the amount the company retains after the cost of serving the customer. Step 2: determine the expected life: if 5% cancel each month, a customer remains 1 / 0.05 = 20 months on average. Step 3: multiply: 45 x 20 = EUR 900, equivalent to dividing the monthly margin by the churn rate. Using the full EUR 60 of revenue would instead give EUR 1,200, crediting the customer with money that is spent on serving them. Observe how much more sensitive the result is to churn than to price: halving the churn rate doubles lifetime value, whereas raising the price by a tenth raises it by only a tenth.

Apply this method for the remainder of the unit: multiply the period's revenue by the gross margin to obtain the amount retained, then divide by the churn rate for the same period. Where a question specifies an average life in periods rather than a churn rate, multiply by that life instead of dividing. No further derivation is required; apply the steps exactly as presented.
