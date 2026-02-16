import streamlit as st
import concurrent.futures
from utils.extractor import extract_data_with_gemini, extract_text_from_pdf
from utils.scorer import calculate_score  # Scorer fonksiyonunu import ettik

if "job_saved" not in st.session_state:
    st.session_state.job_saved = False

if "job_analysis_result" not in st.session_state:
    st.session_state.job_analysis_result = None

st.title("Resume Analyser")
st.markdown("---")

st.subheader("Job Description")
job_desc = st.text_area("Enter the Job Description")

if st.button("Save Job Description"):
    st.session_state.job_saved = True
    st.session_state.job_description = job_desc
    st.session_state.job_analysis_result = None

if st.session_state.job_saved:
    st.success("Job Description Saved!")

    if st.session_state.job_analysis_result is None:
        with st.spinner("Analyzing Job Description..."):
            st.session_state.job_analysis_result = extract_data_with_gemini(
                st.session_state.job_description, 
                type="job_description"
            )

    st.subheader("Resume/CV")
    uploaded_file = st.file_uploader("Upload the Resume/CV", type=["pdf", "txt"], accept_multiple_files=True)

    if uploaded_file:
        st.success("Files Uploaded!")
        st.markdown("---")

        files_data = []
        for i in uploaded_file:
            if i.type == "text/plain":
                text = str(i.read(), "utf-8")
            else:
                text = extract_text_from_pdf(i)
            files_data.append({"name": i.name, "text": text})

        results = []
        with st.spinner("Analyzing All Resumes Simultaneously..."):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_file = {
                    executor.submit(
                        extract_data_with_gemini, 
                        file["text"],              
                        "resume",                  
                        st.session_state.job_analysis_result
                    ): file["name"] for file in files_data
                }

                for future in concurrent.futures.as_completed(future_to_file):
                    name = future_to_file[future]
                    try:
                        data = future.result()
                        results.append({"name": name, "data": data})
                    except Exception as e:
                        results.append({"name": name, "error": str(e)})

        for res in results:
            st.header(res["name"])
            
            if "error" in res:
                st.error(f"Error: {res['error']}")
            else:
                with st.expander("Show Extracted JSON Data"):
                    st.json(res["data"])
                
                score_result = calculate_score(
                    st.session_state.job_analysis_result, 
                    res["data"]
                )
                
                final_score = score_result["final_score"]
                reasoning = score_result["reasoning"]
                breakdown = score_result["breakdown"]

                calculation_steps = score_result.get("calculation_steps", [])

                if final_score >= 80:
                    score_color = "green"
                elif final_score >= 50:
                    score_color = "orange"
                else:
                    score_color = "red"

                st.subheader("Scoring Analysis")
                
                st.markdown(f"""
                <div style="border: 2px solid {score_color}; padding: 20px; border-radius: 10px; text-align: center;">
                    <h1 style="color: {score_color}; margin:0;">{final_score} / 100</h1>
                    <p>Match Score</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Skills (30%)", f"{breakdown['skills']}%", 
                            help="the skills that candidate has / required total skills from job description")
                
                col2.metric("Experience (45%)", f"{breakdown['experience']}%", 
                            help="the experience year that candidate has / required total experience year from job description")
                
                col3.metric("Education (15%)", f"{breakdown['education']}%", 
                            help="candidate education level / required education level from job description")
                
                col4.metric("Bonus (10%)", f"{breakdown['bonus']}%", 
                            help="preferred skills that candidate has / total preferred skills from job description")

                st.write("")

                with st.expander("View Scoring Proof (Deterministic Logic)"):
                    for step in calculation_steps:
                        st.write(step)

                st.markdown("### Detailed Reasoning")
                if not reasoning:
                    st.info("Perfect match! No negative findings.")
                else:
                    for item in reasoning:
                        if "Eliminated" in item:
                            st.error(f"{item}")
                        elif "Missing" in item or "Low" in item or "Little" in item:
                            st.warning(f"{item}")
                        elif "Plus" in item or "Overqualified" in item:
                            st.success(f"{item}") 
                        else:
                            st.info(f"ℹ{item}")

                years = breakdown.get("years_calc", {})
                if years:
                    st.caption(f"""
                    **Experience Calculation Logic:** 
                    Required: {years['required']} years | 
                    Candidate Total: {years['adjusted_total']} adjusted years 
                    (Primary: {years['primary']}y + Secondary: {years['secondary']}y)
                    """)

            st.markdown("---")