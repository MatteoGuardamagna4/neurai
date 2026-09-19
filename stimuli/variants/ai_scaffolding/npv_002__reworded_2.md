---
stimulus_id: npv_002_ai_scaffolding__reworded_2
unit_id: npv_002
condition: ai_scaffolding
variant: reworded_2
---
# Explanation

Let us return to net present value, applied to a different purchase. Every investment involves a trade-off between money paid now and money promised in the future, and the two are not comparable until the future money has been discounted. Net present value restates each future amount in present terms and compares the total with the amount payable immediately. If the restated total is greater, the investment exceeds the return the business requires and should be undertaken; otherwise, the funds are better deployed elsewhere.

Discounting is this restatement. An amount received after one year is divided by one plus the required return, since that is what the money would have earned if invested instead. An amount received after two years has forgone that return twice, so the divisor is squared. The pattern extends to later years, each with its own exponent, which is why the years can never be aggregated prior to division.

For an investment with two years of returns:

NPV = CF1 / (1 + r) + CF2 / (1 + r)^2 - Cost paid today

Worked example. A bakery is offered an oven costing EUR 25,000 today that would save EUR 18,000 of cash at the end of each of the following two years. The bakery requires a 20% return. Year 1: 18,000 / 1.2 = EUR 15,000. Year 2: 18,000 / 1.44 = EUR 12,500. The savings have a present value of EUR 27,500, so the NPV is 27,500 - 25,000 = EUR 2,500, and the oven is worth acquiring.

The characteristic error is to sum the future amounts first. For the bakery, undiscounted savings of EUR 36,000 against an oven costing EUR 25,000 suggest a gain of EUR 11,000, more than four times the correct figure, and the same sum would appear equally favourable were the savings received in ten years rather than two. Timing is the entire purpose of the calculation, so each year is discounted by its own factor before any aggregation. Bear this sequence in mind as you attempt the problem below; should your answer be incorrect, my first question will concern your treatment of the second year's saving.

# Problem

A cafe can buy a coffee machine for EUR 50,000 today. It would save EUR 36,000 of cash at the end of year 1 and EUR 36,000 at the end of year 2. The cafe requires a 20% return a year. What is the net present value of the purchase? Please attempt it yourself first. I shall not disclose the answer: if your result is incorrect, I shall ask a question about your working and provide a hint, after which you may try again.

# Diagnostic questions

Before commenting on your result, I would like to ask three questions.

By what did you divide the year 2 saving, and why does that divisor differ from the one for year 1?

Is EUR 36,000 received in two years worth more or less today than EUR 36,000 received in one?

Consider a calculation of 72,000 - 50,000. What does it assume about the timing of the savings?

# Hints

Hint 1: The two savings are received at different times, so they do not have the same present value and cannot be summed as they stand. Treat each year separately first.

Hint 2: An amount received after one year is divided by one plus the required return. An amount received after two years has waited twice as long, so the divisor is squared.

Hint 3: Sum the two present values, then deduct the amount the cafe pays today. The remainder is the net present value.

The final calculation remains yours to perform.
