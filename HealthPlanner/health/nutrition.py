"""TDEE/BMI helpers (Mifflin–St Jeor) for calorie goals and the maintenance calculator."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional


def lbs_to_kg(weight_lbs: float) -> float:
    return float(weight_lbs) * 0.453592


def ft_to_cm(height_ft: float) -> float:
    """Height stored as decimal feet (e.g. 5.75 ft = 5 ft 9 in). Total inches = height_ft * 12."""
    inches = float(height_ft) * 12.0
    return inches * 2.54


def bmi_from_ft_lbs(weight_lbs: float, height_ft: float) -> float:
    if height_ft <= 0 or weight_lbs <= 0:
        return 0.0
    height_in = float(height_ft) * 12.0
    return round(703.0 * float(weight_lbs) / (height_in**2), 1)


def bmi_category(bmi: float) -> str:
    if bmi <= 0:
        return ""
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "healthy range"
    if bmi < 30:
        return "overweight"
    return "obese"


def _sex_offset(sex: Optional[str]) -> float:
    if sex == "M":
        return 5.0
    if sex == "F":
        return -161.0
    return -78.0


def mifflin_st_jeor_bmr(
    weight_lbs: float,
    height_ft: float,
    age: int,
    sex: Optional[str] = None,
) -> int:
    w_kg = lbs_to_kg(weight_lbs)
    h_cm = ft_to_cm(height_ft)
    bmr = 10 * w_kg + 6.25 * h_cm - 5 * float(age) + _sex_offset(sex)
    return max(int(round(bmr)), 0)


_ACTIVITY_MULT: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "extra": 1.9,
}


def tdee_from_bmr(bmr: int, activity_level: str) -> int:
    mult = _ACTIVITY_MULT.get(activity_level, 1.55)
    return max(int(round(bmr * mult)), 0)


GoalKey = Literal["lose", "gain", "maintain", "muscle gain"]


@dataclass
class GoalSuggestion:
    daily_calories: int
    protein: int
    carbs: int
    fat: int
    note: str


def macro_split(calories: int, protein_g: int, pct_carbs: float, pct_fat: float) -> tuple[int, int]:
    """Fill carbs and fat from remaining calories after protein."""
    remainder = calories - protein_g * 4
    remainder = max(remainder, 0)
    carbs = max(int(round(remainder * pct_carbs / 4)), 0)
    fat = max(int(round(remainder * pct_fat / 9)), 0)
    used = protein_g * 4 + carbs * 4 + fat * 9
    drift = calories - used
    if abs(drift) >= 40:
        carbs = max(carbs + int(round(drift / 4)), 0)
    return carbs, fat


def build_goal_card(
    key: GoalKey,
    tdee: int,
    weight_lbs: float,
    *,
    height_ft: Optional[float],
    onboarding_goal: Optional[str],
    bmi: float,
) -> GoalSuggestion:
    wkg = lbs_to_kg(weight_lbs)
    bmi_bucket = bmi_category(bmi)

    if key == "lose":
        deficit = 500
        if bmi >= 35:
            deficit = 750
        elif bmi >= 28:
            deficit = 600
        elif bmi < 23 and bmi > 0:
            deficit = 300
            note = (
                "With a BMI in or near the \"healthy range\", a modest deficit avoids "
                "undereating. Consider checking with a clinician before aggressive cuts."
            )
        else:
            note = ""

        calories = max(tdee - deficit, 1200 if height_ft else 1300)
        protein = int(round(max(wkg * 1.9, weight_lbs * 0.8)))
        pct_c, pct_f = 0.42, 0.30
        if not note:
            if bmi_bucket in ("overweight", "obese"):
                note = (
                    "Your BMI suggests prioritizing steadier fat loss via protein and modest "
                    "calorie reduction; adjust if your clinician recommends differently."
                )
            elif onboarding_goal == "lose_weight":
                note = "Matched to your sign-up preference to prioritize fat loss sustainably."
            else:
                note = "Balanced macros for gradual weight loss while keeping protein adequate."

        carbs, fat = macro_split(calories, protein, pct_c, pct_f)
        return GoalSuggestion(calories, protein, carbs, fat, note)

    if key == "gain":
        surplus = 400 if weight_lbs < 170 else 450
        if bmi < 22:
            surplus = min(surplus + 100, 700)
        calories = tdee + surplus
        protein = int(round(max(wkg * 1.9, weight_lbs * 0.8)))
        pct_c, pct_f = 0.44, 0.32
        carbs, fat = macro_split(calories, protein, pct_c, pct_f)
        note = (
            "Slight calorie surplus plus higher protein suits lean gain; scale portion sizes "
            "if weight creeps faster than planned."
            if bmi < 26
            else "Surplus geared toward gradual gain; revisit if BMI trends upward quickly."
        )
        return GoalSuggestion(calories, protein, carbs, fat, note)

    if key == "maintain":
        calories = tdee
        protein = int(round(max(wkg * 1.2, weight_lbs * 0.7)))
        carbs, fat = macro_split(calories, protein, 0.40, 0.34)
        note = (
            "Maintenance targets sit near your TDEE (choose activity closest to typical weeks)."
        )
        return GoalSuggestion(calories, protein, carbs, fat, note)

    # muscle gain
    calories = tdee + 250
    protein = int(round(max(wkg * 2.0, weight_lbs * 0.9)))
    carbs, fat = macro_split(calories, protein, 0.43, 0.28)
    note = (
        "Extra calories are modest alongside higher protein—ideal for hypertrophy-focused "
        "training when recovery and sleep align."
        if onboarding_goal == "gain_muscle"
        else "Protein-forward surplus for gradual muscle gain paired with progressive training."
    )
    return GoalSuggestion(calories, protein, carbs, fat, note)


def build_goal_suggestions(
    *,
    weight_lbs: Decimal | float | None,
    height_ft: Decimal | float | None,
    age: int | None,
    sex: str | None,
    onboarding_goal: Optional[str],
    activity_default: str = "moderate",
) -> tuple[dict[str, dict[str, object]], list[str]]:
    blurbs: list[str] = []
    fallback = Decimal("165")
    wt = float(weight_lbs or fallback)

    hg = height_ft if height_ft is not None else Decimal("5.75")
    hf = float(hg)

    ag = max(int(age or 35), 16)

    bmi = bmi_from_ft_lbs(wt, hf)

    sex_code: Optional[str] = sex if sex in ("M", "F") else None
    bmr = mifflin_st_jeor_bmr(wt, hf, ag, sex_code)
    tdee_val = tdee_from_bmr(bmr, activity_default)

    if bmi > 25:
        blurbs.append(
            f"BMI (~{bmi:g}) lands above the \"healthy range\" cutoff (25)—goal suggestions skew "
            "toward sustainable deficits and generous protein unless your clinician directs otherwise."
        )
    elif 0 < bmi < 18.5:
        blurbs.append(
            "BMI is under the usual healthy-range floor—prioritize nourishment and clinician "
            "input before deep deficits."
        )
    elif bmi:
        blurbs.append(f"BMI (~{bmi:g}) sits in common healthy-range bounds.")

    out: dict[str, dict[str, object]] = {}
    for key in ("lose", "gain", "maintain", "muscle gain"):
        card = build_goal_card(
            key,  # type: ignore[arg-type]
            tdee_val,
            wt,
            height_ft=hf,
            onboarding_goal=onboarding_goal,
            bmi=bmi,
        )
        out[key] = {
            "daily_calories": card.daily_calories,
            "protein": card.protein,
            "carbs": card.carbs,
            "fat": card.fat,
            "note": card.note,
        }

    blurbs.insert(
        0,
        f'Rough maintenance (TDEE) with "{activity_default}" activity: ~{tdee_val} cal/day.',
    )

    return out, blurbs


def compute_maintenance(
    *,
    weight_lbs: float,
    height_ft: float,
    age: int,
    sex: Optional[str],
    activity_level: str,
) -> dict[str, object]:
    sex_code = sex if sex in ("M", "F") else None
    bmr = mifflin_st_jeor_bmr(weight_lbs, height_ft, max(int(age), 16), sex_code)
    tdee_val = tdee_from_bmr(bmr, activity_level)
    bmi_val = round(bmi_from_ft_lbs(weight_lbs, height_ft), 1)
    return {
        "bmr": bmr,
        "tdee": tdee_val,
        "bmi_label": bmi_category(bmi_from_ft_lbs(weight_lbs, height_ft)),
        "bmi": bmi_val,
        "activity_level": activity_level,
    }


def dashboard_copy(
    *,
    weight_lbs: Optional[float],
    height_ft: Optional[float],
    age: Optional[int],
    sex: Optional[str],
    onboarding_goal: Optional[str],
) -> tuple[list[str], Optional[float], Optional[int]]:
    if not weight_lbs or not height_ft or not age:
        return (
            ["Add weight, height, and age via your account details for tailored guidance."],
            None,
            None,
        )

    wt = float(weight_lbs)
    hf = float(height_ft)
    bmi = bmi_from_ft_lbs(wt, hf)

    cat = bmi_category(bmi)
    blurbs = [f"Your BMI (~{bmi:g}) is {cat or 'not available'}."]

    if onboarding_goal == "lose_weight":
        blurbs.append(
            "You're aiming to lose weight: favor enough protein (~0.8–1.0 g/lb), mostly whole foods, "
            "and predictable meal timing so your calorie target feels sustainable."
        )
    elif onboarding_goal == "gain_muscle":
        blurbs.append(
            "Hypertrophy works best alongside small caloric surplus, strong protein (~0.85–1.0 g/lb), "
            "and progressively harder training coupled with ample sleep."
        )
    elif onboarding_goal == "maintain_weight":
        blurbs.append(
            "Anchoring macros near TDEE paired with mindful logging keeps fluctuations smaller."
        )

    return blurbs, bmi, tdee_from_bmr(
        mifflin_st_jeor_bmr(wt, hf, max(int(age), 16), sex if sex in ("M", "F") else None),
        "moderate",
    )
