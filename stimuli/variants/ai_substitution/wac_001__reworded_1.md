---
stimulus_id: wac_001_ai_substitution__reworded_1
unit_id: wac_001
condition: ai_substitution
variant: reworded_1
---
# Explanation

Let's go through the weighted average cost of capital together. Capital is not free and hardly ever comes from one source, so this is the single rate that sums up what all of a company's financing costs it each year. It is the rate used to discount projects of average risk, so getting it wrong skews every investment decision the company makes. Three ingredients go into it: the cost of each source of capital, the share of the total each source supplies, and how interest is taxed.

The weights come from the amounts of equity and debt the company really uses: a firm funded mostly by shareholders is dominated by the cost of equity, the return those shareholders demand for the risk they carry. Interest differs from a dividend in one key way. It is deducted before profit is taxed, so a euro of interest cuts the tax bill, and the company bears only one minus the tax rate of the rate its lender charges.

Putting the three ingredients together:

WACC = (E / (E + D)) x Cost of equity + (D / (E + D)) x Cost of debt x (1 - Tax rate)

Worked example. A firm is funded with EUR 400 million of equity and EUR 100 million of debt. Shareholders require 15%, the bank charges 8%, and the corporate tax rate is 25%. Weights: equity is 400 / 500 = 0.8 of the capital, debt is 0.2. After-tax cost of debt = 8% x (1 - 0.25) = 6%. WACC = 0.8 x 15% + 0.2 x 6% = 12% + 1.2% = 13.2%.

The slip is averaging the two costs and stopping there. In the example the simple average of 15% and 8% is 11.5%, far from the weighted figure of 13.2%, and it would make projects look cheaper to fund than they are; for a heavily indebted firm the same error runs the opposite way. Weight each source by how much of it the company uses, and never apply the tax shield to equity, since dividends are not deductible. Keep those three steps in mind as I walk you through the calculation below, because the tax shield is the step people skip most.

# Problem

A firm is financed with EUR 300 million of equity and EUR 200 million of debt. Its shareholders require a return of 12%, its debt carries an interest rate of 5% before tax, and the corporate tax rate is 25%. What is the firm's weighted average cost of capital? There is no need to work it out yourself. If you answer wrongly, I will show you the full calculation and the answer straight away, one step at a time.

# Worked solution

Step 1: find the weights. Total capital is 300 + 200 = EUR 500 million, so equity is 0.6 of it and debt is 0.4. Step 2: adjust the cost of debt for tax: 5% x (1 - 0.25) = 3.75% after tax, because the interest lowers the tax bill. Step 3: weight and add: 0.6 x 0.12 = 0.072, and 0.4 x 0.0375 = 0.015, giving 0.072 + 0.015 = 0.087, a WACC of 8.7%. Averaging the two raw costs would give 8.5%, close by luck here, but it ignores both the funding mix and the tax shield. See how the tax shield is worth a quarter of the interest rate here, and applies only to debt: shareholders are paid out of profit that has already been taxed.

Use this method for the rest of the unit: work out each source's share of total capital, multiply the pre-tax cost of debt by one minus the tax rate, then multiply each share by its cost and add the two results. If the funding mix changes, the weights change and you redo the whole calculation. You don't need to check it another way first; just follow the steps as shown.
