---
stimulus_id: npv_002_ai_substitution__reworded_2
unit_id: npv_002
condition: ai_substitution
variant: reworded_2
---
# Explanation

Let us return to net present value, applied to a different purchase. Every investment involves a trade-off between money paid now and money promised in the future, and the two are not comparable until the future money has been discounted. Net present value restates each future amount in present terms and compares the total with the amount payable immediately. If the restated total is greater, the investment exceeds the return the business requires and should be undertaken; otherwise, the funds are better deployed elsewhere.

Discounting is this restatement. An amount received after one year is divided by one plus the required return, since that is what the money would have earned if invested instead. An amount received after two years has forgone that return twice, so the divisor is squared. The pattern extends to later years, each with its own exponent, which is why the years can never be aggregated prior to division.

For an investment with two years of returns:

NPV = CF1 / (1 + r) + CF2 / (1 + r)^2 - Cost paid today

Worked example. A bakery is offered an oven costing EUR 25,000 today that would save EUR 18,000 of cash at the end of each of the following two years. The bakery requires a 20% return. Year 1: 18,000 / 1.2 = EUR 15,000. Year 2: 18,000 / 1.44 = EUR 12,500. The savings have a present value of EUR 27,500, so the NPV is 27,500 - 25,000 = EUR 2,500, and the oven is worth acquiring.

The characteristic error is to sum the future amounts first. For the bakery, undiscounted savings of EUR 36,000 against an oven costing EUR 25,000 suggest a gain of EUR 11,000, more than four times the correct figure, and the same sum would appear equally favourable were the savings received in ten years rather than two. Timing is the entire purpose of the calculation, so each year is discounted by its own factor before any aggregation. Bear this in mind as I present the calculation below, since the exponent of the second year is the step most commonly omitted.

# Problem

A cafe can buy a coffee machine for EUR 50,000 today. It would save EUR 36,000 of cash at the end of year 1 and EUR 36,000 at the end of year 2. The cafe requires a 20% return a year. What is the net present value of the purchase? It is not necessary to solve this yourself. Should your answer be incorrect, I shall present the complete calculation and the answer immediately, step by step.

# Worked solution

Step 1: discount year 1: 36,000 / 1.2 = EUR 30,000. Step 2: discount year 2 for two years of waiting: 36,000 / 1.44 = EUR 25,000. Step 3: the savings have a present value of 30,000 + 25,000 = EUR 55,000. Step 4: deduct the price paid now: 55,000 - 50,000 = EUR 5,000. The NPV is positive, so the machine earns more than the 20% the cafe requires. Summing the undiscounted savings would instead give 72,000 - 50,000 = EUR 22,000, treating money not yet received as though it were already in the till. Observe that the two savings are equal in size but not in value: the first is worth EUR 30,000 today and the second only EUR 25,000, and the difference increases with each additional year of waiting.

Apply this method for the remainder of the unit: divide each year's cash by one plus the rate raised to the number of that year, sum the present values, then deduct the amount paid today. Where the required return changes, recalculate every factor rather than adjusting the previous result. Apply the steps exactly as presented.
