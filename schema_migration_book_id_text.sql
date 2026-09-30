-- ====================================================================
-- SUPABASE SCHEMA MIGRATION: BOOK ID AS TEXT PRIMARY KEY & CASCADE
-- ====================================================================

-- Step 1: Drop foreign key constraints on 'exhibitor' (both potential constraint names)
ALTER TABLE IF EXISTS exhibitor DROP CONSTRAINT IF EXISTS exhibitors_book_id_fkey CASCADE;
ALTER TABLE IF EXISTS exhibitor DROP CONSTRAINT IF EXISTS exhibitor_book_id_fkey CASCADE;
ALTER TABLE IF EXISTS exhibitors DROP CONSTRAINT IF EXISTS exhibitors_book_id_fkey CASCADE;
ALTER TABLE IF EXISTS exhibitors DROP CONSTRAINT IF EXISTS exhibitor_book_id_fkey CASCADE;

-- Step 2: Drop identity / autoincrement sequence from books.id
ALTER TABLE IF EXISTS books ALTER COLUMN id DROP IDENTITY IF EXISTS;

-- Step 3: Alter books.id to TEXT (converting existing numeric IDs to text)
ALTER TABLE IF EXISTS books ALTER COLUMN id TYPE TEXT USING id::text;

-- Step 4: Alter exhibitor.book_id to TEXT (converting existing numeric IDs to text)
ALTER TABLE IF EXISTS exhibitor ALTER COLUMN book_id TYPE TEXT USING book_id::text;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'exhibitors') THEN
        ALTER TABLE exhibitors ALTER COLUMN book_id TYPE TEXT USING book_id::text;
    END IF;
END $$;

-- Step 5: Ensure book_name is NOT UNIQUE (drop unique constraints on book_name so identical names are allowed)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT conname 
        FROM pg_constraint 
        WHERE conrelid = 'books'::regclass 
        AND contype = 'u'
    ) LOOP
        EXECUTE 'ALTER TABLE books DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname);
    END LOOP;
END $$;

-- Step 6: Re-add Foreign Key Constraint with ON UPDATE CASCADE & ON DELETE CASCADE
ALTER TABLE IF EXISTS exhibitor 
ADD CONSTRAINT exhibitor_book_id_fkey 
FOREIGN KEY (book_id) REFERENCES books(id) 
ON UPDATE CASCADE ON DELETE CASCADE;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'exhibitors') THEN
        ALTER TABLE exhibitors 
        ADD CONSTRAINT exhibitors_book_id_fkey 
        FOREIGN KEY (book_id) REFERENCES books(id) 
        ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;
END $$;
