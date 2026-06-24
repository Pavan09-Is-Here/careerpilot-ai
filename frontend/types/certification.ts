export type CertificationInput = {
  name: string;
  issuing_organization: string;
  credential_id: string | null;
  credential_url: string | null;
  issue_date: string;
  expiry_date: string | null;
  does_not_expire: boolean;
  description: string | null;
  skills: string[];
  verified: boolean;
};

export type Certification =
  CertificationInput & {
    id: number;
    candidate_profile_id: number;
    created_at: string;
    updated_at: string;
  };