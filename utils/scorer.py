# Deterministic Python Algorithm is done here

import datetime

# Skill Level Weights
SKILL_LEVEL_WEIGHTS = {
    "Unspecified": 1.0,
    "Basic": 1.0,       
    "Intermediate": 1.2, 
    "Advanced": 1.5,     
    "Expert": 2.0        
}

REQUIRED_LEVEL_WEIGHTS = {
    "Unspecified": 1.0,
    "Junior": 1.0,
    "Senior": 1.5,
    "Lead": 2.0
}

EXPERIENCE_RELEVANCE_WEIGHTS = {
    "Primary": 1.0,
    "Secondary": 0.5,
    "Irrelevant": 0.0
}

EDUCATION_LEVEL_MAPPING = {
    "None": 0,
    "High School": 1,
    "Associate": 2,
    "Bachelor": 3,
    "Master": 4,
    "PhD": 5,
    "Doctorate": 5
}

# Calculating the Date
def calculate_months_between(start_date_str, end_date_str):
    if not start_date_str or start_date_str.lower() == "unknown":
        return set()
    
    try:
        start = datetime.datetime.strptime(start_date_str, "%Y-%m")
    except ValueError:
        return set()
    
    if not end_date_str or end_date_str.lower() == "present":
        end = datetime.datetime.now()
    else:
        try:
            end = datetime.datetime.strptime(end_date_str, "%Y-%m")
        except ValueError:
            end = datetime.datetime.now()

    months_set = set()
    curr = start
    while curr <= end:
        months_set.add(curr.strftime("%Y-%m"))
        if curr.month == 12:
            curr = datetime.datetime(curr.year + 1, 1, 1)
        else:
            curr = datetime.datetime(curr.year, curr.month + 1, 1)
            
    return months_set

# Calculating the total experience duration
def calculate_total_experience(work_history):
    primary_months_set = set()
    secondary_months_set = set()

    if not work_history:
        return {"primary_years": 0.0, "secondary_years": 0.0}
    
    for role in work_history:
        start = role.get("start", "Unknown")
        end = role.get("end", "Present")
        relevance = role.get("relevance", "Irrelevant")

        role_months = calculate_months_between(start, end)

        if relevance == "Primary":
            primary_months_set.update(role_months)
        elif relevance == "Secondary":
            secondary_months_set.update(role_months)

    secondary_months_set = secondary_months_set - primary_months_set

    return {
        "primary_years": round(len(primary_months_set) / 12, 1),
        "secondary_years": round(len(secondary_months_set) / 12, 1)
    }

# Main Function : Scoring Candidate
def calculate_score(job_data, candidate_data):

    # Calculating Experience Duration
    exp_calc = calculate_total_experience(candidate_data.get("work_history", [])) 
    primary_years = exp_calc["primary_years"]
    secondary_years = exp_calc["secondary_years"]

    # Skills of candidates
    cand_skills_map = {
        s['name'].lower(): s.get('level', 'Unspecified') 
        for s in candidate_data.get('skills', [])
    }

    cand_licenses = set(l.lower() for l in candidate_data.get('licenses', []))

    required_licenses = job_data.get('required_licenses', [])
    if required_licenses:
        for req_lic in required_licenses:
            req_lic_lower = req_lic.lower()
            
            if "/" in req_lic_lower or " or " in req_lic_lower:
                options = [opt.strip() for opt in req_lic_lower.replace("/", " or ").split(" or ")]
                
                has_one_of_the_options = any(opt in cand_licenses for opt in options)
                
                if not has_one_of_the_options:
                    return {
                        "final_score": 0,
                        "reasoning": [f"Eliminated: Missing one of the required license options: {req_lic}"],
                        "breakdown": {"skills": 0, "experience": 0, "education": 0, "bonus": 0}
                    }
            
            # If it's a standard, single license requirement
            elif req_lic_lower not in cand_licenses:
                return {
                    "final_score": 0,
                    "reasoning": [f"Eliminated: Compulsory License Missing: {req_lic}"],
                    "breakdown": {"skills": 0, "experience": 0, "education": 0, "bonus": 0}
                }
    
    # Location Check - If not remote        
    is_remote = job_data.get('is_remote_allowed', False)
    job_loc = job_data.get('location', '').lower()
    cand_loc = candidate_data.get('location', 'Unknown').lower()

    if job_loc and job_loc != "unspecified" and not is_remote:
        if cand_loc != "unknown":
            if cand_loc not in job_loc and job_loc not in cand_loc:
                return {
                    "final_score": 0,
                    "reasoning": [f"Eliminated: Location not Match. \nJob: {job_data.get('location')}, \nCandidate: {candidate_data.get('location')}."],
                    "breakdown": {"skills": 0, "experience": 0, "education": 0, "bonus": 0}
                }
        
    # Core Scoring
    reasoning = []

    # Skill Scoring (45%)
    job_required_skills = job_data.get('required_skills', [])

    # If no mandatory skills are specified in the job description, full marks are awarded.
    if not job_required_skills:
        skill_score = 100
        reasoning.append("No required skills specified (Full Score).")
    else:
        total_skill_points = 0
        max_possible_points = 0

        for skill in job_required_skills:
            skill_name = skill['name'].lower()
            
            req_level = skill.get('level', 'Unspecified')
            req_weight = REQUIRED_LEVEL_WEIGHTS.get(req_level, 1.0)
            max_possible_points += req_weight 
            
            if skill_name in cand_skills_map:
                cand_level = cand_skills_map[skill_name]
                cand_weight = SKILL_LEVEL_WEIGHTS.get(cand_level, 1.0)
            
                earned = min(cand_weight, req_weight)
                
                total_skill_points += earned
                
                if cand_weight > req_weight:
                     reasoning.append(f"Overqualified Skill: {skill['name']} (Expert vs {req_level})")
            else:
                reasoning.append(f"Missing Skill: {skill['name']}")

        raw_skill_score = (total_skill_points / max_possible_points) * 100
        skill_score = min(raw_skill_score, 100)

    # Experience Scoring (30%)
    req_exp_years = job_data.get('min_experience_years', 0)

    adjusted_candidate_years = (primary_years * 1.0) + (secondary_years * 0.5)

    if req_exp_years == 0:
        exp_score = 100
        reasoning.append("No experience required (Full score).")

    else:
        exp_ratio = adjusted_candidate_years / req_exp_years
        exp_score = min(exp_ratio * 100, 100)

        if exp_score < 100:
            reasoning.append(f"Little Experience: \nRequired: {req_exp_years} years, \nCandidate: {adjusted_candidate_years} years \n(Primary+Sec).")

    # Education Scoring (15%)
    job_edu_level = job_data.get('education_level', 'None')
    cand_edu_level = candidate_data.get('education_level', 'None')

    job_edu_val = EDUCATION_LEVEL_MAPPING.get(job_edu_level, 0)
    cand_edu_val = EDUCATION_LEVEL_MAPPING.get(cand_edu_level, 0)

    if cand_edu_val >= job_edu_val:
        edu_score = 100
    else:
        diff = job_edu_val - cand_edu_val
        edu_score = max(100 - (diff * 25), 0)
        reasoning.append(f"Low Education Level: \nRequired: {job_edu_level}, \nCandidate: {cand_edu_level}.")

    # Nice to Have Scoring (10%)
    job_preferred_skills = job_data.get('preferred_skills', [])
    
    if not job_preferred_skills:
        bonus_score = 100
    else:
        match_count = 0
        total_pref = len(job_preferred_skills)
        
        for skill in job_preferred_skills:
            if skill['name'].lower() in cand_skills_map:
                match_count += 1
        
        bonus_score = (match_count / total_pref) * 100
        if bonus_score > 0:
            reasoning.append(f"Plus Points: {match_count}/{total_pref} preferred skill available.")

    # Aggregation
    final_score = (
        (skill_score * 0.30) +
        (exp_score * 0.45) +
        (edu_score * 0.15) +
        (bonus_score * 0.10)
    )
 
    calc_steps = [
        f"1. Skills: ({round(total_skill_points, 1)} / {round(max_possible_points, 1)}) * 100 = {round(skill_score, 1)}% | Weight: 30% | Contribution: {round(skill_score * 0.30, 2)} [the skills that candidate has / required total skills from job description]",
        f"2. Experience: ({round(adjusted_candidate_years, 1)} / {max(req_exp_years, 1)}) * 100 = {round(exp_score, 1)}% | Weight: 45% | Contribution: {round(exp_score * 0.45, 2)} [the experience year that candidate has / required total experience year from job description]",
        f"3. Education: Score: {round(edu_score, 1)}% | Weight: 15% | Contribution: {round(edu_score * 0.15, 2)} [candidate education level / required education level from job description]",
        f"4. Bonus: ({match_count} / {max(total_pref, 1)}) * 100 = {round(bonus_score, 1)}% | Weight: 10% | Contribution: {round(bonus_score * 0.10, 2)} [preferred skills that candidate has / total preferred skills from job description]",
        f"TOTAL SCORE = {round(skill_score * 0.30, 2)} + {round(exp_score * 0.45, 2)} + {round(edu_score * 0.15, 2)} + {round(bonus_score * 0.10, 2)} = {round(final_score, 1)}"
    ]

    return {
        "final_score": round(final_score, 1),
        "reasoning": reasoning,
        "calculation_steps": calc_steps,
        "breakdown": {
            "skills": round(skill_score, 1),
            "experience": round(exp_score, 1),
            "education": round(edu_score, 1),
            "bonus": round(bonus_score, 1),
            "years_calc": {
                "required": req_exp_years,
                "primary": primary_years,
                "secondary": secondary_years,
                "adjusted_total": adjusted_candidate_years
            }
        }
    }