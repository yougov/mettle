BEGIN;

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
    INSERT INTO change_records ("table",operation,definition_id,old)
      VALUES (TG_TABLE_NAME, TG_OP, OLD.id, row_to_json(OLD));
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER services_audit_trig AFTER UPDATE OR INSERT OR DELETE ON services
    FOR EACH ROW EXECUTE PROCEDURE services_audit_trig_func();

-- Audit changes on 'pipelines' table
CREATE OR REPLACE FUNCTION pipelines_audit_trig_func() RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_records ("table",operation,row_id,who,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(NEW));
  ELSIF (TG_OP = 'UPDATE') THEN
    INSERT INTO change_records ("table",operation,row_id,who,old,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(OLD), row_to_json(NEW));
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_records ("table",operation,definition_id,old)
      VALUES (TG_TABLE_NAME, TG_OP, OLD.id, row_to_json(OLD));
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pipelines_audit_trig AFTER UPDATE OR INSERT OR DELETE ON pipelines
    FOR EACH ROW EXECUTE PROCEDURE pipelines_audit_trig_func();


-- Audit changes on 'notification_lists' table
CREATE OR REPLACE FUNCTION notification_lists_audit_trig_func() RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_records ("table",operation,row_id,who,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(NEW));
  ELSIF (TG_OP = 'UPDATE') THEN
    INSERT INTO change_records ("table",operation,row_id,who,old,new)
      VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.updated_by, row_to_json(OLD), row_to_json(NEW));
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_records ("table",operation,definition_id,old)
      VALUES (TG_TABLE_NAME, TG_OP, OLD.id, row_to_json(OLD));
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notification_lists_audit_trig AFTER UPDATE OR INSERT OR DELETE ON notification_lists
    FOR EACH ROW EXECUTE PROCEDURE notification_lists_audit_trig_func();

INSERT INTO migration_history (name) VALUES ('0003-add-change-triggers');
COMMIT;
