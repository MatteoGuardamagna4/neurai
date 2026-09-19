---
stimulus_id: npv_001_traditional__reworded_1
unit_id: npv_001
condition: traditional
variant: reworded_1
---
# Explanation

A euro you receive in two years is worth less than a euro you receive today, because today's euro can be invested and would have grown by then. Net present value applies that idea to a project. It converts every future cash flow into today's money and compares the total with what has to be paid now. If the total is bigger, the project earns more than the return the company requires and adds value; if it is smaller, it does not.

Turning a future amount into today's money is called discounting. Cash that arrives in one year is divided by one plus the required return. Cash that arrives in two years has waited twice as long, so it is divided by one plus the required return squared, and later years get higher powers still. The required return is what the company could earn elsewhere for the same risk, so discounting at that rate asks whether the project beats the alternative.

For a project with two years of cash flows:

NPV = CF1 / (1 + r) + CF2 / (1 + r)^2 - Cost paid today

Worked example. A machine costs EUR 40,000 today and should bring in EUR 30,000 of cash at the end of year 1 and EUR 30,000 at the end of year 2. The company wants a 25% return. Year 1: 30,000 / 1.25 = EUR 24,000. Year 2: 30,000 / 1.25 squared = 30,000 / 1.5625 = EUR 19,200. The inflows are worth EUR 43,200 today, so the NPV is 43,200 - 40,000 = EUR 3,200 and the machine is worth buying.

The slip is adding up the future cash flows and subtracting the cost, or discounting their total just once. For the machine the raw total of EUR 60,000 against a cost of EUR 40,000 suggests a gain of EUR 20,000, more than six times the real figure, and it would look just as good if the same cash turned up in year ten. Discount each year by its own factor, because the whole point of the calculation is that timing matters. The order is: discount each flow, add the results, then take off what is paid today. A positive answer means the project beats the return the company requires.

# Problem

A project costs EUR 100,000 today and is expected to generate EUR 72,000 of cash at the end of year 1 and EUR 72,000 at the end of year 2. The required return is 20% a year. What is the net present value of the project? Try it on your own. If you get it wrong, you will get up to three hints, one at a time, and a new attempt after each.

# Hints

Hint 1: Money that arrives later is worth less than the same money today, so you cannot just add the two inflows. Handle each year on its own before you compare anything with the cost.

Hint 2: Year 1's cash is divided by one plus the rate. Year 2's cash has waited twice as long, so it is divided by one plus the rate squared.

Hint 3: Add the two present values you found and subtract what is paid today. What is left is the net present value.

# Worked solution

Step 1: discount year 1: 72,000 / 1.2 = EUR 60,000. Step 2: discount year 2 for two years of waiting: 72,000 / 1.2 squared = 72,000 / 1.44 = EUR 50,000. Step 3: add the present values: 60,000 + 50,000 = EUR 110,000. Step 4: take off what is paid today: 110,000 - 100,000 = EUR 10,000. The NPV is positive, so the project earns more than the 20% required and is worth doing. Adding the raw cash flows would have given 144,000 - 100,000 = EUR 44,000, which counts money that has not arrived yet at its full value.
