export type HindsightConfig = {
  apiUrl: string;
  apiKey: string;
};

export function loadHindsightConfig(): HindsightConfig | null {
  const apiUrl = process.env.HINDSIGHT_API_URL?.trim() ?? "";
  const apiKey = process.env.HINDSIGHT_API_TENANT_API_KEY?.trim() ?? "";
  if (!apiUrl || !apiKey) return null;
  return { apiUrl: apiUrl.replace(/\/+$/, ""), apiKey };
}
