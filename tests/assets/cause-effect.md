# Causal Chains: Northgate Distribution Center Incident Report

This report documents three independent causal chains that contributed to a 14-day operational shutdown at the Northgate Distribution Center in October 2024.

## Chain 1: Cooling System Failure → Inventory Loss

Northgate's warehouse management system was upgraded in August 2024 without updating the HVAC control integration layer. The integration layer continued sending thermostat setpoints in Fahrenheit to a new controller that expected Celsius. On October 3rd, the cold-storage zone reached 18°C (64°F) instead of the target 4°C, causing $1.2M of temperature-sensitive pharmaceutical inventory to exceed safe storage thresholds within 36 hours. The root cause was the failure to update unit conversions during the software migration.

## Chain 2: Staff Scheduling Error → Delayed Detection

The facility's quality assurance team uses a rotating on-call schedule managed in a shared spreadsheet. In September, a clerical error removed the overnight QA supervisor from the October 3rd rotation without notifying backup coverage. As a result, no qualified supervisor was on-site to review the automated temperature alerts that fired at 2:14 AM. The alerts were escalated by the monitoring system at 6:00 AM when the day shift arrived, by which point the inventory damage was complete. The root cause was the absence of automated validation in the scheduling process.

## Chain 3: Insurance Lapse → Extended Shutdown

Northgate's property and inventory insurance policy was due for renewal on October 1st. A billing dispute with the insurer — caused by a name discrepancy introduced during a corporate rebrand in July — delayed renewal paperwork. The facility operated without active coverage for the first four days of October. When the inventory loss was discovered on October 4th, the insurance claim was rejected for the damage occurring during the lapse window. Northgate's legal team pursued arbitration, and the resulting freeze on financial reserves prevented the company from immediately purchasing replacement inventory, extending the shutdown from an estimated 3 days to 14 days. The root cause was the failure to reconcile entity name discrepancies before the policy renewal deadline.
