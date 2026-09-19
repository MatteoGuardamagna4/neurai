---
stimulus_id: wac_002_ai_substitution__reworded_1
unit_id: wac_002
condition: ai_substitution
variant: reworded_1
---
# Explanation

Let's revisit the weighted average cost of capital, this time for another firm. A company borrowing at 8% while its shareholders want 12% faces neither figure as its cost of capital. The weighted average cost of capital is the single rate that stands for what all of a company's financing costs it each year. It is the rate used to discount projects of ordinary risk, so an error in it skews every investment decision the company makes, always in the same direction, for as long as the error lasts.

Three ingredients go into it. Each source has its own cost: shareholders demand a return for the risk they carry, and lenders quote an interest rate. Each source supplies a share of the total capital, and those shares are the weights. And interest, unlike a dividend, is deducted before profit is taxed, so a euro of interest lowers the tax bill and the company bears only one minus the tax rate of the quoted rate.

Putting the three together:

WACC = (E / (E + D)) x Cost of equity + (D / (E + D)) x Cost of debt x (1 - Tax rate)

Worked example. A firm is funded half by equity and half by debt. Shareholders require 16%, the bank charges 10%, and the tax rate is 20%. After-tax cost of debt = 10% x (1 - 0.20) = 8%. WACC = 0.5 x 16% + 0.5 x 8% = 8% + 4% = 12%.

The slip is averaging the two costs and stopping. The firm in the example happens to be funded half and half, so the weights are equal and the average looks harmless, but the tax shield still counts: ignoring it would show 13% instead of 12%. In a firm funded mostly one way, the weights matter far more than the shield, and a simple average can be off by several points in either direction. Never apply the shield to equity: dividends are not deductible. Keep those three steps in mind as I walk you through the calculation below, because the tax shield is the step people skip most.

# Problem

A firm is financed with EUR 150 million of equity and EUR 50 million of debt. Its shareholders require a return of 12%, its debt carries an interest rate of 8% before tax, and the corporate tax rate is 25%. What is the firm's weighted average cost of capital? There is no need to work it out yourself. If you answer wrongly, I will show you the full calculation and the answer straight away, one step at a time.

# Worked solution

Step 1: the weights. Total capital is 150 + 50 = EUR 200 million, so equity supplies 0.75 of it and debt 0.25. Step 2: the tax shield. An 8% interest rate costs the firm 8% x (1 - 0.25) = 6% after tax. Step 3: weight and add: 0.75 x 0.12 = 0.09, and 0.25 x 0.06 = 0.015, giving 0.09 + 0.015 = 0.105, a WACC of 10.5%. A simple average of 12% and 8% would give 10%, which lands nearby here only because the numbers are mild; it ignores that three quarters of this firm's capital is the expensive kind. See how much work the weights are doing: three quarters of this firm's capital carries the 12% cost, which is why the answer sits much nearer 12% than the after-tax cost of its debt.

Use this method for the rest of the unit: work out each source's share of total capital, multiply the quoted cost of debt by one minus the tax rate, then multiply each share by its cost and add. If the funding mix changes, redo the weights and start again. Follow the steps exactly as shown.
