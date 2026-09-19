---
stimulus_id: npv_001_ai_substitution__reworded_2
unit_id: npv_001
condition: ai_substitution
variant: reworded_2
---
# Explanation

Let us examine net present value together. It rests on a single principle: a euro received in two years is worth less than a euro received today, since a euro available today can be invested and would have grown in the interval. Net present value applies this principle to a project. It expresses each future cash flow in present terms and compares the total with the amount payable now. If the total is greater, the project earns more than the company's required return and creates value; if it is smaller, it does not.

Expressing a future amount in present terms is known as discounting. Cash received after one year is divided by one plus the required return. Cash received after two years has waited twice as long, so it is divided by one plus the required return squared, and subsequent years carry correspondingly higher powers. The required return is what the company could earn elsewhere at equivalent risk, so discounting at that rate tests whether the project outperforms the alternative.

For a project with two years of cash flows:

NPV = CF1 / (1 + r) + CF2 / (1 + r)^2 - Cost paid today

Worked example. A machine costs EUR 40,000 today and is expected to generate EUR 30,000 of cash at the end of year 1 and EUR 30,000 at the end of year 2. The company requires a 25% return. Year 1: 30,000 / 1.25 = EUR 24,000. Year 2: 30,000 / 1.25 squared = 30,000 / 1.5625 = EUR 19,200. The present value of the inflows is EUR 43,200, so the NPV is 43,200 - 40,000 = EUR 3,200, and the machine is worth acquiring.

The characteristic error is to sum the future cash flows and deduct the cost, or to discount their sum only once. In the machine example the undiscounted sum of EUR 60,000 against a cost of EUR 40,000 suggests a gain of EUR 20,000, more than six times the true figure, and it would appear equally attractive were the same cash received in year ten. Each year must be discounted by its own factor, since the entire purpose of the calculation is to reflect timing. Bear this in mind as I present the calculation below, since the exponent of the second year is the step most commonly omitted.

# Problem

A project costs EUR 100,000 today and is expected to generate EUR 72,000 of cash at the end of year 1 and EUR 72,000 at the end of year 2. The required return is 20% a year. What is the net present value of the project? It is not necessary to solve this yourself. Should your answer be incorrect, I shall present the complete calculation and the answer immediately, step by step.

# Worked solution

Step 1: discount year 1: 72,000 / 1.2 = EUR 60,000. Step 2: discount year 2 for two years of waiting: 72,000 / 1.2 squared = 72,000 / 1.44 = EUR 50,000. Step 3: sum the present values: 60,000 + 50,000 = EUR 110,000. Step 4: deduct the amount paid today: 110,000 - 100,000 = EUR 10,000. The NPV is positive, so the project earns more than the required 20% and is worth undertaking. Summing the undiscounted cash flows would instead have given 144,000 - 100,000 = EUR 44,000, valuing money not yet received at its full amount. Observe that the two inflows are equal in size but not in value: the first is worth EUR 60,000 today and the second only EUR 50,000.

Apply this method for the remainder of the unit: discount each year's cash by one plus the rate raised to the number of that year, sum the present values, then deduct the amount paid today. Where the required return changes, recalculate from the beginning rather than adjusting the previous result, since every factor changes. No alternative route is required; apply the steps exactly as presented.
