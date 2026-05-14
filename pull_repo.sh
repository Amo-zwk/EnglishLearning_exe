#!/usr/bin/env bash
set -euo pipefail

cd /d/EnglishLearning
git status
git pull
git log --oneline -5
