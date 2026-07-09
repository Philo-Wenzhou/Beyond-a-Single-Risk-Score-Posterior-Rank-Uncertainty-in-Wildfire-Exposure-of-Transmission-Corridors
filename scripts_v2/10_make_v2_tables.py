from utils_v2 import PROJECT, require_audit_first, write_text


def main():
    require_audit_first()
    manifest = PROJECT / "outputs/v2/tables/TABLE_MANIFEST.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("table_id,file,script,source_table,manuscript_section,caption_short,status\n", encoding="utf-8")
    note = PROJECT / "outputs/v2/audit/V2_TABLES_NOT_RUN.md"
    write_text(note, "# V2 Tables Not Run\n\nNo V2 result tables were generated because model outputs do not exist yet.\n")
    raise SystemExit(f"V2 tables not yet generated; see {note}")


if __name__ == "__main__":
    main()
