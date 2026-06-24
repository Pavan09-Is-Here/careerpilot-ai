import type {
  CandidateProfile,
  CandidateProfileInput,
} from "@/types/candidate";

import type {
  Education,
  EducationInput,
} from "@/types/education";

import type {
  Experience,
  ExperienceInput,
} from "@/types/experience";

import type {
  Project,
  ProjectInput,
} from "@/types/project";

import type {
  Skill,
  SkillInput,
} from "@/types/skill";

import type {
  Certification,
  CertificationInput,
} from "@/types/certification";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

export type HealthResponse = {
  service: string;
  status: string;
  version: string;
};

type ValidationError = {
  msg?: string;
  loc?: Array<string | number>;
};

type ErrorResponse = {
  detail?: string | ValidationError[];
};

async function readErrorMessage(
  response: Response,
): Promise<string> {
  try {
    const body =
      (await response.json()) as ErrorResponse;

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (Array.isArray(body.detail)) {
      return body.detail
        .map((error) => {
          const location = error.loc
            ?.filter(
              (item) =>
                item !== "body" &&
                item !== "query" &&
                item !== "path",
            )
            .join(".");

          const message =
            error.msg ?? "Validation error";

          return location
            ? `${location}: ${message}`
            : message;
        })
        .join(", ");
    }
  } catch {
    // The response did not contain JSON.
  }

  return `Request failed with status ${response.status}`;
}

/*
|--------------------------------------------------------------------------
| Backend health
|--------------------------------------------------------------------------
*/

export async function getBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(
    `${API_URL}/api/health`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<HealthResponse>;
}

/*
|--------------------------------------------------------------------------
| Candidate profile
|--------------------------------------------------------------------------
*/

export async function getCandidateProfile(): Promise<
  CandidateProfile | null
> {
  const response = await fetch(
    `${API_URL}/api/profile`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<CandidateProfile>;
}

export async function saveCandidateProfile(
  profile: CandidateProfileInput,
): Promise<CandidateProfile> {
  const response = await fetch(
    `${API_URL}/api/profile`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(profile),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<CandidateProfile>;
}

/*
|--------------------------------------------------------------------------
| Education
|--------------------------------------------------------------------------
*/

export async function getEducationRecords(): Promise<
  Education[]
> {
  const response = await fetch(
    `${API_URL}/api/education`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Education[]>;
}

export async function createEducation(
  education: EducationInput,
): Promise<Education> {
  const response = await fetch(
    `${API_URL}/api/education`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(education),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Education>;
}

export async function updateEducation(
  educationId: number,
  education: EducationInput,
): Promise<Education> {
  const response = await fetch(
    `${API_URL}/api/education/${educationId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(education),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Education>;
}

export async function deleteEducation(
  educationId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/education/${educationId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Work experience
|--------------------------------------------------------------------------
*/

export async function getExperienceRecords(): Promise<
  Experience[]
> {
  const response = await fetch(
    `${API_URL}/api/experience`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Experience[]>;
}

export async function createExperience(
  experience: ExperienceInput,
): Promise<Experience> {
  const response = await fetch(
    `${API_URL}/api/experience`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(experience),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Experience>;
}

export async function updateExperience(
  experienceId: number,
  experience: ExperienceInput,
): Promise<Experience> {
  const response = await fetch(
    `${API_URL}/api/experience/${experienceId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(experience),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Experience>;
}

export async function deleteExperience(
  experienceId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/experience/${experienceId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Projects
|--------------------------------------------------------------------------
*/

export async function getProjectRecords(): Promise<
  Project[]
> {
  const response = await fetch(
    `${API_URL}/api/projects`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Project[]>;
}

export async function createProject(
  project: ProjectInput,
): Promise<Project> {
  const response = await fetch(
    `${API_URL}/api/projects`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(project),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Project>;
}

export async function updateProject(
  projectId: number,
  project: ProjectInput,
): Promise<Project> {
  const response = await fetch(
    `${API_URL}/api/projects/${projectId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(project),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Project>;
}

export async function deleteProject(
  projectId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/projects/${projectId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Skills
|--------------------------------------------------------------------------
*/

export async function getSkillRecords(): Promise<
  Skill[]
> {
  const response = await fetch(
    `${API_URL}/api/skills`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Skill[]>;
}

export async function createSkill(
  skill: SkillInput,
): Promise<Skill> {
  const response = await fetch(
    `${API_URL}/api/skills`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(skill),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Skill>;
}

export async function updateSkill(
  skillId: number,
  skill: SkillInput,
): Promise<Skill> {
  const response = await fetch(
    `${API_URL}/api/skills/${skillId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(skill),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Skill>;
}

export async function deleteSkill(
  skillId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/skills/${skillId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}
/*
|--------------------------------------------------------------------------
| Certifications
|--------------------------------------------------------------------------
*/

export async function getCertificationRecords(): Promise<
  Certification[]
> {
  const response = await fetch(
    `${API_URL}/api/certifications`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<
    Certification[]
  >;
}

export async function createCertification(
  certification: CertificationInput,
): Promise<Certification> {
  const response = await fetch(
    `${API_URL}/api/certifications`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(certification),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Certification>;
}

export async function updateCertification(
  certificationId: number,
  certification: CertificationInput,
): Promise<Certification> {
  const response = await fetch(
    `${API_URL}/api/certifications/${certificationId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(certification),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Certification>;
}

export async function deleteCertification(
  certificationId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/certifications/${certificationId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}