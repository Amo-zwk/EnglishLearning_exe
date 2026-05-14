#!/usr/bin/env bash
set -euo pipefail

cd /d
git clone https://github.com/Amo-zwk/EnglishLearning.git
cd EnglishLearning
git log --oneline -5
