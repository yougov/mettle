BEGIN;

-- migration 0003 accidentally had a 'definition_id' in the DELETE branches of these statements,
-- which had been copy/pasted from another project.

-- Audit changes on 'services' table    
CREATE OR REPLACE FUNCTION services_audit_trig_func() RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_records ("table",operation,row_id,who,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(NEW));
  ELSIF (TG_OP = 'UPDATE') THEN
    INSERT INTO change_records ("table",operation,row_id,who,old,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(OLD), row_to_json(NEW));
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_records ("table",operation,row_id,old)
      VALUES (TG_TABLE_NAME, TG_OP, OLD.id, row_to_json(OLD));
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pipelines_audit_trig_func() RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_records ("table",operation,row_id,who,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(NEW));
  ELSIF (TG_OP = 'UPDATE') THEN
    INSERT INTO change_records ("table",operation,row_id,who,old,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(OLD), row_to_json(NEW));
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_records ("table",operation,row_id,old)
      VALUES (TG_TABLE_NAME, TG_OP, OLD.id, row_to_json(OLD));
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION notification_lists_audit_trig_func() RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_records ("table",operation,row_id,who,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(NEW));
  ELSIF (TG_OP = 'UPDATE') THEN
    INSERT INTO change_records ("table",operation,row_id,who,old,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(OLD), row_to_json(NEW));
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_records ("table",operation,row_id,old)
      VALUES (TG_TABLE_NAME, TG_OP, OLD.id, row_to_json(OLD));
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$ LANGUAGE plpgsql;

INSERT INTO migration_history (name) VALUES ('0009-fix-change-triggers');
COMMIT;
