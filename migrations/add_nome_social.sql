-- Nome social (opcional): nome pelo qual a pessoa prefere ser tratada.
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS nome_social varchar(150);
