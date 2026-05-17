import { useEffect, useState } from "react";
import { api } from "../api/client";
import "../components/forms.css";

type Props = {
  title: string;
  endpoint: string;
  note?: string;
};

export default function FoundationListPage({ title, endpoint, note }: Props) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    api<Record<string, unknown>[]>(endpoint).then(setRows).catch(() => setRows([]));
  }, [endpoint]);

  const keys = rows[0] ? Object.keys(rows[0]) : ["id"];

  return (
    <>
      <h1 className="page-title">{title}</h1>
      {note && <p className="status-msg">{note}</p>}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>{keys.map((k) => <th key={k}>{k}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={String(r.id || i)}>
                {keys.map((k) => (
                  <td key={k}>{String(r[k] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="status-msg">No records yet (foundation table ready).</p>}
      </div>
    </>
  );
}
