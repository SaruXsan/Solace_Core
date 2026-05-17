import { useEffect, useState } from "react";
import { enterpriseApi, type Company } from "../api/enterprise";
import "../components/forms.css";

export default function BranchesPage() {
  const [branches, setBranches] = useState<Record<string, unknown>[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);

  useEffect(() => {
    Promise.all([enterpriseApi.branches.list(), enterpriseApi.companies.list()]).then(([b, c]) => {
      setBranches(b);
      setCompanies(c);
    });
  }, []);

  return (
    <>
      <h1 className="page-title">Branches / Sites</h1>
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th>Company</th>
              <th>City</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {branches.map((b) => (
              <tr key={String(b.id)}>
                <td>{String(b.name)}</td>
                <td>{String(b.code)}</td>
                <td>{companies.find((c) => c.id === b.organization_id)?.name || "—"}</td>
                <td>{String(b.city || "—")}</td>
                <td>{b.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
