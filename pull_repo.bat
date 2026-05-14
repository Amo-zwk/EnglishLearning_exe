@echo off
setlocal

cd /d D:\EnglishLearning
git status
git pull
git log --oneline -5
pause
