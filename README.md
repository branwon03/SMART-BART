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

## Coding & Collaboration Conventions

- Use semantic commit messages (see `CONTRIBUTING.md` for full details).
- Open an Issue for every distinct unit of work (lab task, feature, bug, refactor, research).
- Create branches from `main` named after the Issue: `<type>/short-kebab` (e.g., `feat/scheduler-phase1`).
- Commit changes incrementally with semantic commit messages.
- Open a Pull Request early (draft) and link the Issue.
- Request peer review (if required) before merging.
- Squash merge or rebase to keep `main` linear (unless told otherwise).

### MOBILE APP DEVELOPMENT SETUP

The system now makes use of a native mobile app that communicates with the FastAPI backend using your local network. 
Note on Geolocation: We transitioned to a native app to solve the metadata stripping issue found in mobile browsers. This allows our backend to extract exact coordinates directly from the image files even if the user submits the report after leaving the incident site.

1. Prerequisite: Local Environment Setup
Since the mobile app runs on a physical device or emulator, it cannot use localhost. You must point it to your computer's local IP address.

Navigate to src/mobile/.

Create a .env file (this is already in .gitignore).

Add the following line, replacing the IP with your machine's actual local IP:

EXPO_PUBLIC_API_BASE_URL=http://10.56.194.213:8000
(Note: You can find your IP on Windows by running ipconfig in PowerShell).

2. Install & Start
Run the following commands to start the Metro bundler:

Bash
cd src/mobile
npm install
npx expo start

3. Running on your device
Download the Expo Go app on your Android or iOS device.

Ensure your phone and computer are on the same Wi-Fi network.

Scan the QR code displayed in your terminal.

4. Backend Connection & Troubleshooting
Ensure the correct IP address is in your src/mobile/.env file. If you switched WIFI networks, you will need to update it.
FastAPI: Ensure that docker is running before attempting to submit reports.

