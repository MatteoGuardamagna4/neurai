---
stimulus_id: npv_002_ai_substitution__reworded_1
unit_id: npv_002
condition: ai_substitution
variant: reworded_1
---
# Explanation

Let's revisit net present value, this time for another purchase. Every investment weighs money paid now against money promised later, and the two cannot be compared until the later money has been discounted. Net present value converts each future amount into today's money and compares the total with what has to be paid straight away. If the converted total is bigger, the investment beats the return the business requires and is worth making; if not, the money is better spent elsewhere.

Discounting is that conversion. An amount that arrives in a year is divided by one plus the required return, because that is what the money would have earned if invested instead. An amount that arrives in two years has missed that return twice, so the divisor is squared. The pattern carries on for later years, each with its own exponent, which is why the years can never be lumped together before dividing.

For an investment with two years of returns:

NPV = CF1 / (1 + r) + CF2 / (1 + r)^2 - Cost paid today

Worked example. A bakery is offered an oven that costs EUR 25,000 today and would save EUR 18,000 of cash at the end of each of the next two years. The bakery wants a 20% return. Year 1: 18,000 / 1.2 = EUR 15,000. Year 2: 18,000 / 1.44 = EUR 12,500. The savings are worth EUR 27,500 today, so the NPV is 27,500 - 25,000 = EUR 2,500 and the oven is worth buying.

The slip is adding up the future amounts first. For the bakery the raw savings of EUR 36,000 against a EUR 25,000 oven suggest a gain of EUR 11,000, over four times the honest figure, and the same sum would look just as good if the savings came in ten years rather than two. Timing is the whole point of the calculation, so each year is discounted by its own factor before anything is added. Keep that in mind as I walk you through the calculation below, because the second year's exponent is the step people skip most.

# Problem

A cafe can buy a coffee machine for EUR 50,000 today. It would save EUR 36,000 of cash at the end of year 1 and EUR 36,000 at the end of year 2. The cafe requires a 20% return a year. What is the net present value of the purchase? There is no need to work it out yourself. If you answer wrongly, I will show you the full calculation and the answer straight away, one step at a time.

# Worked solution

Step 1: discount year 1: 36,000 / 1.2 = EUR 30,000. Step 2: discount year 2 for two years of waiting: 36,000 / 1.44 = EUR 25,000. Step 3: the savings are worth 30,000 + 25,000 = EUR 55,000 in today's money. Step 4: take off the price paid now: 55,000 - 50,000 = EUR 5,000. The NPV is positive, so the machine earns more than the 20% the cafe requires. Adding the raw savings would give 72,000 - 50,000 = EUR 22,000 and would treat money that has not arrived yet as though it were already in the till. See how the two savings are the same size but not the same value: the first is worth EUR 30,000 today and the second only EUR 25,000, and the gap widens with each extra year of waiting.

Use this method for the rest of the unit: divide each year's cash by one plus the rate raised to that year's number, add the present values, then take off what is paid today. When the required return changes, redo every factor rather than adjusting the old answer. Follow the steps exactly as shown.
