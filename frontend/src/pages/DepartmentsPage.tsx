import { useEffect, useState } from "react";
import { enterpriseApi } from "../api/enterprise";
import "../components/forms.css";

export default function DepartmentsPage() {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    enterpriseApi.departments.list().then(setRows);
  }, []);

  return (
    <>
      <h1 className="page-title">Departments / Business Units</h1>
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th>Company ID</th>
              <th>Branch</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={String(d.id)}>
                <td>{String(d.name)}</td>
                <td>{String(d.code)}</td>
                <td>{String(d.organization_id)}</td>
                <td>{d.branch_id ? String(d.branch_id) : "—"}</td>
                <td>{d.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
