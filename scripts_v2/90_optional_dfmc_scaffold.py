from utils_v2 import PROJECT, require_audit_first, write_text


ENABLE_DFMC = False


def main():
    require_audit_first()
    note = PROJECT / "outputs/v2/audit/DFMC_NOT_RUN.md"
    write_text(
        note,
        "# DFMC Not Run\n\n"
        "ENABLE_DFMC is false. No verified hourly forcing audit has been completed, so no DFMC features or results are produced.\n",
    )
    print(note)


if __name__ == "__main__":
    main()
