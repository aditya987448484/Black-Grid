export interface CompanySearchResult {
  symbol: string;
  name: string;
  exchange?: string;
  sector?: string;
  assetType?: string;
  matchScore?: number;
}

export interface CompanySearchResponse {
  query: string;
  results: CompanySearchResult[];
  count: number;
}
