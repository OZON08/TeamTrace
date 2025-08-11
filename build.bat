@echo off
echo ######################## TeamTrace App Build ########################

echo Delete pre-build folder
rmdir /s/q build
rmdir /s/q dist

echo Build Application EXE
pyinstaller app.spec

echo Copy config file
xcopy /y config.yaml dist\

echo Copy Readme
xcopy /y README.md dist\

echo Copy Changelog
xcopy /y CHANGELOG.md dist\

echo Copy Licence
xcopy /y LICENCE dist\

echo Build process finished

echo ######################## TeamTrace App Build ########################