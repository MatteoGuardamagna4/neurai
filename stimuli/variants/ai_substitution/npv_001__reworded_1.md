---
stimulus_id: npv_001_ai_substitution__reworded_1
unit_id: npv_001
condition: ai_substitution
variant: reworded_1
---
# Explanation

Let's go through net present value together. It rests on one idea: a euro you receive in two years is worth less than a euro you receive today, because today's euro can be invested and would have grown by then. Net present value applies that idea to a project. It converts every future cash flow into today's money and compares the total with what has to be paid now. If the total is bigger, the project earns more than the return the company requires and adds value; if it is smaller, it does not.

Turning a future amount into today's money is called discounting. Cash that arrives in one year is divided by one plus the required return. Cash that arrives in two years has waited twice as long, so it is divided by one plus the required return squared, and later years get higher powers still. The required return is what the company could earn elsewhere for the same risk, so discounting at that rate asks whether the project beats the alternative.

For a project with two years of cash flows:

NPV = CF1 / (1 + r) + CF2 / (1 + r)^2 - Cost paid today

Worked example. A machine costs EUR 40,000 today and should bring in EUR 30,000 of cash at the end of year 1 and EUR 30,000 at the end of year 2. The company wants a 25% return. Year 1: 30,000 / 1.25 = EUR 24,000. Year 2: 30,000 / 1.25 squared = 30,000 / 1.5625 = EUR 19,200. The inflows are worth EUR 43,200 today, so the NPV is 43,200 - 40,000 = EUR 3,200 and the machine is worth buying.

The slip is adding up the future cash flows and subtracting the cost, or discounting their total just once. For the machine the raw total of EUR 60,000 against a cost of EUR 40,000 suggests a gain of EUR 20,000, more than six times the real figure, and it would look just as good if the same cash turned up in year ten. Discount each year by its own factor, because the whole point of the calculation is that timing matters. Keep that in mind as I walk you through the calculation below, because the second year's power is the step people skip most.

# Problem

A project costs EUR 100,000 today and is expected to generate EUR 72,000 of cash at the end of year 1 and EUR 72,000 at the end of year 2. The required return is 20% a year. What is the net present value of the project? There is no need to work it out yourself. If you answer wrongly, I will show you the full calculation and the answer straight away, one step at a time.

# Worked solution

Step 1: discount year 1: 72,000 / 1.2 = EUR 60,000. Step 2: discount year 2 for two years of waiting: 72,000 / 1.2 squared = 72,000 / 1.44 = EUR 50,000. Step 3: add the present values: 60,000 + 50,000 = EUR 110,000. Step 4: take off what is paid today: 110,000 - 100,000 = EUR 10,000. The NPV is positive, so the project earns more than the 20% required and is worth doing. Adding the raw cash flows would have given 144,000 - 100,000 = EUR 44,000, which counts money that has not arrived yet at its full value. See how the two inflows are the same size but not the same value: the first is worth EUR 60,000 today, the second only EUR 50,000.

Use this method for the rest of the unit: discount each year's cash by one plus the rate raised to that year's number, add the present values, then take off what is paid today. If the required return changes, start again from the beginning rather than tweaking the old answer, because every factor moves. You don't need to try another route first; just follow the steps as shown.
