/** RFC 9457 Problem Details returned by the backend. */
export interface Problem {
  type: string;
  title: string;
  status: number;
  detail?: string;
  correlation_id?: string | null;
  errors?: { loc: (string | number)[]; msg: string }[];
}

export class ApiError extends Error {
  constructor(public readonly problem: Problem) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
  }

  get status(): number {
    return this.problem.status;
  }
}

export async function toApiError(res: Response): Promise<ApiError> {
  try {
    return new ApiError((await res.json()) as Problem);
  } catch {
    return new ApiError({ type: "about:blank", title: res.statusText, status: res.status });
  }
}
