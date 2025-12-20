# Prompt: Generate Summary of Markdown Files and Project Documentation

## Objective
Read all `.md` files in the project (except `README.md` and `helpme.md`), summarize their content, and generate two files:

1. `README.md` in the project root, with a general summary.
2. `resources/helpme.md` with user help based on the contents.

## Instructions for Copilot
- Go through all `.md` files in the project, ignoring `README.md` and `helpme.md`.
- For each file, extract the first significant lines (titles, subtitles, descriptions).
- Generate a general project summary in `README.md`, grouping contents by file.
- Create or update the `resources/helpme.md` file with user help based on the `.md` contents.
- If the `resources` folder does not exist, create it.
- Maintain Markdown formatting in both files.
- Do not modify the original content of `.md` files, only create summaries.

## Usage Example
> Use the `resume-md` prompt to update the project documentation.
