import { useEffect, useState } from "react";
import { complianceApi, type RfiSection } from "../api/platform";
import "../components/forms.css";

export default function RFICenterPage() {
  const [sections, setSections] = useState<RfiSection[]>([]);
  const [active, setActive] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    complianceApi.rfiSections().then((s) => {
      setSections(s);
      const d: Record<string, string> = {};
      s.forEach((sec) => sec.questions.forEach((q) => { d[q.id] = q.answer_text || ""; }));
      setDrafts(d);
    });
  }, []);

  const sec = sections[active];

  return (
    <>
      <h1 className="page-title">RFI Center</h1>
      <p className="status-msg">Seven compliance sections for RFI readiness.</p>
      {msg && <p className="status-msg ok">{msg}</p>}

      <div className="tabs">
        {sections.map((s, i) => (
          <button key={s.section} type="button" className={`tab ${i === active ? "active" : ""}`} onClick={() => setActive(i)}>
            {s.title.split(" ")[0]}
          </button>
        ))}
      </div>

      {sec && (
        <div className="card">
          <h2 style={{ fontSize: "1rem", marginBottom: "1rem", color: "var(--accent)" }}>{sec.title}</h2>
          {sec.questions.map((q) => (
            <div key={q.id} style={{ marginBottom: "1.25rem" }}>
              <p style={{ fontWeight: 600, marginBottom: "0.35rem" }}>{q.question_code}</p>
              <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>{q.question_text}</p>
              <textarea
                rows={4}
                style={{ width: "100%", background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", borderRadius: 6, padding: "0.5rem" }}
                value={drafts[q.id] || ""}
                onChange={(e) => setDrafts({ ...drafts, [q.id]: e.target.value })}
              />
              <button
                className="btn-secondary"
                style={{ marginTop: "0.35rem" }}
                onClick={async () => {
                  await complianceApi.saveAnswer(q.id, drafts[q.id] || "", "draft");
                  setMsg(`Saved answer for ${q.question_code}`);
                }}
              >
                Save draft
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
