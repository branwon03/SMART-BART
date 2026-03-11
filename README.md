# Image Based Incident Identification and Cataloging

Project Description

## Overview

Project details

### Goals

List main objectives, problems you aim to solve.

### Features

- [x] Feature 1

- [x] Feature 2

- [ ] add some sort of database catalog

- \[ \]

### Software Stack / Technologies Used

- Language: ...
- Framework: ...
- Database: ...
- etc...

## Quickstart

### Prerequisites

- **Python 3.12+**
- [**uv**](https://docs.astral.sh/uv/) — fast Python package manager

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/cse120-ucm/S26-CSE-312
   cd S26-CSE-312
   ```

2. Install all dependencies (creates a virtual environment automatically):

   ```bash
   uv sync
   ```

3. Obtain an NVIDIA API key:

   - Open [NVIDIA Nemotron-Nano](https://build.nvidia.com/nvidia/nemotron-nano-12b-v2-vl) and sign up / log in.
   - Select **View Code**, then click **Generate API Key**.

4. Create a `.env` file in the project root:

   ```bash
   echo "NVIDIA_API_KEY=<your_nvidia_api_key>" > .env
   ```

### Running the FastAPI Server

Start the development server:

```bash
uv run fastapi dev
```

The server starts at **http://127.0.0.1:8000** with interactive API docs at **http://127.0.0.1:8000/docs**.

### API Endpoints

- **POST** `/report` — classify a maintenance incident from images and/or a text description.
  - `media` (file upload, optional) — one or more images (`.png`, `.jpg`, `.jpeg`, `.webp`)
  - `description` (form field, optional) — a short text summary of the incident

## Structure

Include: what constitutes passing (e.g., all tests green, coverage threshold).

## Coding & Collaboration Conventions

- Use semantic commit messages (see `CONTRIBUTING.md` for full details).
- Open an Issue for every distinct unit of work (lab task, feature, bug, refactor, research).
- Create branches from `main` named after the Issue: `<type>/short-kebab` (e.g., `feat/scheduler-phase1`).
- Commit changes incrementally with semantic commit messages.
- Open a Pull Request early (draft) and link the Issue.
- Request peer review (if required) before merging.
- Squash merge or rebase to keep `main` linear (unless told otherwise).