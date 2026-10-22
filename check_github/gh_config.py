API = "https://api.github.com"
SEV_PENALTY_REPO = {"high": 40, "medium": 20, "low": 5, "info": 0}
SEV_PENALTY_PROFILE = {"high": 25, "medium": 12, "low": 4, "info": 0}
PROFILE_PENALTY_CAP = 40
REPO_CAP_TUTORIAL = 55
DUMP_MAX_COMMITS = 2
DUMP_MIN_ADDITIONS = 1500
DUMP_MIN_FILES = 30
DUMP_MIN_SIZE_KB = 500
LARGE_INITIAL_ADDITIONS = 3000
BACKDATE_GAP_DAYS = 90
BACKDATE_MIN_COMMITS = 5
BACKDATE_WINDOW_SECONDS = 86400
BURST_MIN_COMMITS = 15
BURST_WINDOW_SECONDS = 600
LOW_SHARE = 0.30
NEW_ACCOUNT_DAYS = 30
MOSTLY_FORKS_RATIO = 0.7
TIMELINE_SLACK_DAYS = 180
FLAG_CATALOG = {
    "PROFILE_NOT_FOUND": ("medium", "profile", "API", "Linked GitHub profile does not exist (typo or fake link)."),
    "PROFILE_NOT_A_USER": ("low", "profile", "API", "Linked profile is an organization, not a person."),
    "NO_PUBLIC_REPOS": ("low", "profile", "API", "Profile exists but has no public repositories."),
    "NEW_ACCOUNT": ("low", "profile", "API", "Account is less than 30 days old."),
    "ACCOUNT_YOUNGER_THAN_CLAIM": ("low", "profile", "API", "Account is much younger than the claimed years of experience (soft signal)."),
    "MOSTLY_FORKS": ("low", "profile", "API", "Most public repos are forks."),
    "NO_ORIGINAL_REPOS": ("low", "profile", "API", "No original (non-fork) repositories could be analysed."),
    "IDENTITY_NAME_MISMATCH": ("low", "profile", "API", "GitHub display name and login share nothing with the resume name."),
    "SKILL_LANGUAGE_MISMATCH": ("low", "profile", "API", "Most claimed programming languages do not appear in the analysed repos."),
    "CLAIM_NOT_FOUND": ("info", "profile", "API", "Some resume projects match no repository (could be private work)."),
    "PROMPT_INJECTION_ATTEMPT": ("high", "any", "Regex", "Text aimed at manipulating an AI scorer was found in a repo, bio, commit message or the resume."),
    "FORK_NO_CONTRIBUTION": ("high", "repo", "API", "Claimed repo is a fork and the candidate has no commits in it."),
    "LINKED_REPO_NO_CONTRIBUTION": ("high", "repo", "API", "Resume links a repo owned by someone else and the candidate has no commits in it."),
    "SINGLE_COMMIT_DUMP": ("medium", "repo", "API", "1-2 commits carrying a large codebase (bulk upload, not iterative work)."),
    "LARGE_INITIAL_COMMIT": ("low", "repo", "API", "First commit is very large (imported or scaffolded project)."),
    "BACKDATED_COMMITS": ("medium", "repo", "API", "Many commits authored months before they were recorded, all recorded within a day."),
    "BURST_COMMITS": ("low", "repo", "API", "15+ commits recorded within 10 minutes (script, import or rebase)."),
    "ZERO_OWN_COMMITS": ("medium", "repo", "API", "Candidate's own repo contains no commits attributable to the candidate."),
    "LOW_OWN_COMMIT_SHARE": ("low", "repo", "API", "Candidate wrote under 30% of the commits (team project or copied history)."),
    "LICENSE_HOLDER_MISMATCH": ("low", "repo", "API", "LICENSE names a copyright holder unrelated to the candidate."),
    "TIMELINE_MISMATCH": ("low", "repo", "API", "Repo history starts long after the dates the resume gives for the project."),
    "COPIED_REPO_INDICATORS": ("medium", "repo", "API", "Two or more independent copy signals fire on the same repo (high if ownership evidence is also missing)."),
    "DEFAULT_README": ("low", "repo", "Regex", "README is the stock starter-template text."),
    "BOILERPLATE_FILES": ("low", "repo", "API", "Repo still contains default starter-kit files (CRA, Vite, Next.js)."),
    "COMMITTED_DEPENDENCIES": ("low", "repo", "API", "node_modules / venv committed to the repo."),
    "ENV_FILE_COMMITTED": ("low", "repo", "API", "A .env file is committed (hygiene / secrets risk)."),
    "NO_README": ("low", "repo", "API", "Repository has no README."),
    "TUTORIAL_CLONE": ("low", "repo", "LLM", "Repo looks like a well-known beginner tutorial or starter (LLM verdict backed by a verified quote)."),
    "CLAIM_MISMATCH": ("medium", "repo", "LLM", "Repo is clearly much smaller or different than the resume claims (LLM verdict backed by a verified quote)."),
}
STRUCTURAL = {"SINGLE_COMMIT_DUMP", "ZERO_OWN_COMMITS", "BACKDATED_COMMITS", "BURST_COMMITS"}
SUPPORTING = {"LICENSE_HOLDER_MISMATCH", "TIMELINE_MISMATCH", "LOW_OWN_COMMIT_SHARE",
              "LARGE_INITIAL_COMMIT", "BOILERPLATE_FILES"}