-- Optional defence-in-depth: PostgreSQL Row-Level Security for SAMPURNA.
--
-- The API enforces access rules in application code (services/access.py) and is
-- covered by tests. These policies add a database-level backstop when the API
-- connects as a NON-superuser role (e.g. `sampurna_app`) and sets, per request:
--     SELECT set_config('app.user_id', '<uuid>', true);
-- On Supabase, replace current_setting('app.user_id') with auth.uid().
-- Not applied by default migrations; review and apply deliberately.

CREATE OR REPLACE FUNCTION app_uid() RETURNS uuid LANGUAGE sql STABLE AS
$$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$;

CREATE OR REPLACE FUNCTION app_can_view(subject uuid, scope text) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT subject = app_uid() OR EXISTS (
    SELECT 1 FROM access_grants g
    WHERE g.user_id = subject AND g.grantee_id = app_uid() AND g.status = 'active'
      AND g.scopes::jsonb ? scope AND (g.expires_at IS NULL OR g.expires_at > now()))
$$;

ALTER TABLE assessment_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY assess_read ON assessment_sessions FOR SELECT USING (app_can_view(user_id, 'assessments'));
CREATE POLICY assess_write ON assessment_sessions FOR INSERT WITH CHECK (user_id = app_uid() OR app_can_view(user_id, 'interviews'));

ALTER TABLE wellness_category_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY scores_read ON wellness_category_scores FOR SELECT USING (app_can_view(user_id, 'assessments'));

ALTER TABLE assessment_responses ENABLE ROW LEVEL SECURITY;
CREATE POLICY responses_read ON assessment_responses FOR SELECT USING (EXISTS (
  SELECT 1 FROM assessment_sessions s WHERE s.assessment_id = assessment_responses.assessment_id AND app_can_view(s.user_id, 'assessments')));

ALTER TABLE micro_habit_tracking ENABLE ROW LEVEL SECURITY;
CREATE POLICY habits_own ON micro_habit_tracking USING (user_id = app_uid()) WITH CHECK (user_id = app_uid());

ALTER TABLE interview_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY interviews_read ON interview_records FOR SELECT USING (user_id = app_uid() OR (interviewer_id = app_uid() AND app_can_view(user_id, 'interviews')));

ALTER TABLE interview_transcripts ENABLE ROW LEVEL SECURITY;
CREATE POLICY transcripts_read ON interview_transcripts FOR SELECT USING (app_can_view(owner_user_id, 'interviews'));

ALTER TABLE professional_observations ENABLE ROW LEVEL SECURITY;
CREATE POLICY obs_read ON professional_observations FOR SELECT USING (counselor_id = app_uid() AND app_can_view(user_id, 'observations'));

ALTER TABLE consent_and_privacy ENABLE ROW LEVEL SECURITY;
CREATE POLICY consent_own ON consent_and_privacy USING (user_id = app_uid()) WITH CHECK (user_id = app_uid());
