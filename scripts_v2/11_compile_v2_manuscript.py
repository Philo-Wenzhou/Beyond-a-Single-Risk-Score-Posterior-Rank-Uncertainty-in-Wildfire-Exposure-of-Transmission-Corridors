from utils_v2 import PROJECT, require_audit_first, write_text


def main():
    require_audit_first()
    tex = PROJECT / "manuscript_v2/main_v2_spatiotemporal.tex"
    if not tex.exists():
        write_text(
            tex,
            r"""\documentclass[11pt]{article}
\begin{document}
\title{Temporal Persistence, Spatial Support, and Posterior Rank Stability in Public-Data Wildfire Exposure Screening of Transmission-Line Segments}
\author{}
\date{}
\maketitle

This V2 manuscript scaffold is intentionally empty of results. The V2 prompt
requires audit, support-aligned covariates, temporal-process features, model
fits, validation, and figure/table generation before manuscript claims are
written.

\end{document}
""",
        )
    note = PROJECT / "outputs/v2/audit/V2_MANUSCRIPT_NOT_COMPILED.md"
    write_text(note, "# V2 Manuscript Not Compiled\n\nThe TeX scaffold exists, but no V2 results have been generated or compiled.\n")
    raise SystemExit(f"V2 manuscript not compiled; see {note}")


if __name__ == "__main__":
    main()
