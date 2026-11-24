from pathlib import Path
root=Path(__file__).resolve().parent
admin=(root/'web/src/AdminSetup.tsx').read_text()
importer=(root/'web/src/DataQualityImporter.tsx').read_text()
assert '<DataQualityImporter onImported={onChanged}/>' in admin
assert 'Company setup & HRIS settings' in admin
assert all(x in admin for x in ["navigate('orgsettings')","navigate('accounts')","navigate('dataquality')","navigate('audit')"])
assert all(x in importer for x in ["'/settings'","'/preview'","'/commit'","'/history'","duplicate_mode","date_format","sheet_name","max_rows"])
assert 'onImported?:()=>Promise<void>' in importer
print('PASS: shared Company Setup HRIS importer, settings, import refresh and navigation checks')
