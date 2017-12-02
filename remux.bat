@echo off
set FN=%~dpn1
set SUFFIX=%2
set SRC_FLAGS=--no-audio --no-subtitles --no-track-tags --no-attachments --no-buttons --no-chapters --no-global-tags
set ENC_FLAGS=--no-video
mkvmerge -o "%FN%_mux.mkv" %SRC_FLAGS% "%FN%_%2.mkv" %ENC_FLAGS% "%FN%.mkv"