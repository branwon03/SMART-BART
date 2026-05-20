<div align="center">

# Image Based Incident Identification and Cataloging

An automated web application that detects, classifies, and de-duplicates BART maintenance incident reports submitted via image uploads, reducing manual workload for BART staff and improving infrastructure monitoring across the Bay Area.

CSE-312 | UC Merced School of Engineering <br><br>
</div>

Project Partner: Bay Area Rapid Transit (BART) <br>
Mentors: Christian Chaves & Julio Flores Molina


## Overview

BART's current incident reporting pipeline is entirely manual and lacks the scalability to handle surges in maintenance reports. With infrastructure spanning five counties, the volume of incoming reports far exceeds what limited staff can realistically process, resulting in duplicated or unresolved issues.

This project bridges that gap by building an image-based system that automatically classifies submitted photos, groups duplicate reports of the same incident, and surfaces de-duplicated issues to the correct BART department through a maintenance dashboard.

## The Team
- Akash Sant: anagtode@ucmerced.edu - Back-End Developer, Team Lead
- Kiara Cuntapay: kcuntapay@ucmerced.edu - ML/CV Engineer, Data Engineer
- Brandon Wong: bwong77@ucmerced.edu - Front-End Engineer, ML/CV Engineer
- Emma Countryman: ecountryman@ucmerced.edu - Data Engineer, ML/CV Engineer
- Gavin Abrigo: gabrigo@ucmerced.edu - DevOps Engineer, ML/CV Engineer 

### Goals
- Automate the classification and routing of image-based incident reports.
- Reduce duplicate incident reports through ML-powered de-duplication.
- Provide BART staff with a consolidated maintenance dashboard.
- Enable incident ingestion via both web app and email.

### Features

Required:
- [ ] Photo subject detection & routing
- [ ] Incident de-duplication
- [ ] Ingestion via web app & email
- [ ] Photo confidence scoring

Bonus:
- [ ] Face blurring
- [ ] Video processing

### Software Stack / Technologies Used

- Frontend: Next.js
- Backend: Python / FastAPI
- Detection Model: Nvidia Nemotron-Nano 12b (multimodal VLM) (TBD)
- Grouping Model: CLIP ViT-B-16 via SentenceTransformers
- Data Processing: scikit-learn (Cosine Similarity)
- Image Storage: Amazon S3
- Database: Amazon DynamoDB
(Subject to change)

## Quickstart

See the Software Stack & Quick Start wiki page for full setup instructions for the frontend, backend, and ML service.

### Instructions

1. Click "Use this template" on GitHub to create your private repository.
2. Clone your repo locally.
3. Fill in the metadata table above.
4. Create an initial branch (e.g., `setup`), never commit directly to `main` (unless instructed).
5. Open an Issue for each lab / feature before starting work.
6. Use Pull Requests to merge changes (each PR should reference at least one Issue).

## Structure

Include: what constitutes passing (e.g., all tests green, coverage threshold).

## Local development (Docker)

Default stack (**no profiles**):

- `docker compose up` — Postgres, FastAPI backend, Next.js frontend (processor, Gmail polling, tunnel, and mobile containers stay **off**).

Optional profiles (**combine as needed**):

| Need | Command |
|------|---------|
| Vertex / upload pipeline / background processor + Gmail ingestion | `docker compose --profile workers up` |
| Public HTTPS URL for Next (tunnel to `frontend:3000`) | `docker compose --profile tunnel up` |
| Dockerized Expo (+ tunnel automatically via `mobile` profile on tunnel service) | `docker compose --profile mobile up` |

Multiple profiles:

```bash
docker compose --profile workers --profile tunnel up
```

Environment variable equivalent (persist in shell/profile):

```bash
export COMPOSE_PROFILES=workers,tunnel
docker compose up
```

**Breaking change:** `docker compose up` no longer starts `processor`, `gmail-worker`, `cloudflare-tunnel`, or `mobile`. If CI or teammates relied on implicit “bring everything up,” add `--profile workers` (and others) explicitly.

## Coding & Collaboration Conventions

- Use semantic commit messages (see `CONTRIBUTING.md` for full details).
- Open an Issue for every distinct unit of work (lab task, feature, bug, refactor, research).
- Create branches from `main` named after the Issue: `<type>/short-kebab` (e.g., `feat/scheduler-phase1`).
- Commit changes incrementally with semantic commit messages.
- Open a Pull Request early (draft) and link the Issue.
- Request peer review (if required) before merging.
- Squash merge or rebase to keep `main` linear (unless told otherwise).

## MOBILE APP DEVELOPMENT SETUP

The system now makes use of a native mobile app that communicates with the FastAPI backend using LAN. 
Note on Geolocation: We transitioned to a native app to solve the metadata stripping issue found in mobile browsers. This allows our backend to extract exact coordinates directly from the image files even if the user submits the report after leaving the incident site.

1. Prerequisite: Local Environment Setup
Since the mobile app runs on a physical device or emulator, it cannot use localhost. You must point it to your computer's local IP address.

      - **In src/mobile/**, create a .env file (this is already handled in .gitignore).

      - Add the following line, replacing the IP with your machine's actual local IP: 

              EXPO_PUBLIC_API_BASE_URL=http://10.56.194.213:8000

           (Note: You can find your IP on Windows by running ipconfig in PowerShell).


3. Install & Start
      - Run the following commands to start the Metro bundler:

            Bash
            cd src/mobile
            npm install
            npx expo start

3. Running on your device
      - Download the Expo Go app on your Android or iOS device.

      - Ensure your phone and computer are on the same Wi-Fi network.

      - Scan the QR code displayed in your terminal.

4. Backend Connection & Troubleshooting
      - Ensure the correct IP address is in your src/mobile/.env file. If you switched WIFI networks, you will need to update it.
      - FastAPI: Ensure that docker is running before attempting to submit reports, or the submit button will hang and fail.
      - If you are still running into issues connecting, you may need to add python and node.js to the list of allowed apps on your computer. 
      - If all else fails, turn on mobile hotspot on your phone and connect your PC to it and try again.

