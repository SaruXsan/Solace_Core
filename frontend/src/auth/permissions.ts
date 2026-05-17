export type PermissionSet = Set<string> | string[];

function toSet(permissions: PermissionSet): Set<string> {
  return permissions instanceof Set ? permissions : new Set(permissions);
}

export function hasPermission(permissions: PermissionSet, name: string): boolean {
  const set = toSet(permissions);
  if (set.has("*")) return true;
  return set.has(name);
}

export function hasAnyPermission(permissions: PermissionSet, names: string[]): boolean {
  const set = toSet(permissions);
  if (set.has("*")) return true;
  return names.some((n) => set.has(n));
}

export function hasAllPermissions(permissions: PermissionSet, names: string[]): boolean {
  const set = toSet(permissions);
  if (set.has("*")) return true;
  return names.every((n) => set.has(n));
}
