; An older build packed the game into resources\app.asar, which Electron loads before resources\app.
; Remove it so an install over an old version runs the new game.
; The exe keeps Electron's icon (editing it gets it blocked by Smart App Control), so point the
; shortcuts and the Installed apps entry at the game's own icon file instead.
!macro customInstall
  Delete "$INSTDIR\resources\app.asar"
  CreateShortCut "$DESKTOP\${SHORTCUT_NAME}.lnk" "$appExe" "" "$INSTDIR\resources\app\icon.ico" 0
  CreateShortCut "$SMPROGRAMS\${SHORTCUT_NAME}.lnk" "$appExe" "" "$INSTDIR\resources\app\icon.ico" 0
  WriteRegStr SHCTX "${UNINSTALL_REGISTRY_KEY}" "DisplayIcon" "$INSTDIR\resources\app\icon.ico"
!macroend
