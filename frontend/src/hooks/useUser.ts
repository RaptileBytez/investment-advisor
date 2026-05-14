import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

/** Shared current-user query. Single source of truth across the app. */
export function useUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.me(),
    staleTime: 5 * 60_000,
  });
}
