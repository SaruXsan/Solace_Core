/** Shown when the user has read permission but not update for a settings area. */

export default function ReadOnlyNotice() {
  return (
    <p className="status-msg" style={{ marginBottom: "0.75rem" }}>
      You have read-only access.
    </p>
  );
}
