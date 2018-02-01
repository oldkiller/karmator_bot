-- create base table
CREATE TABLE karma_user (
	userid int NOT NULL,
	chatid int NOT NULL,
	karma int NULL DEFAULT 0,
	user_name char(100) NULL,
	user_nick char(50) NULL,
	is_banned bool,
	PRIMARY KEY (userid,chatid))

-- create table for limiting karm
CREATE TABLE limitation (
	userid int not null,
	chatid int not null,
	timer TIMESTAMP not NULL)

-- сreate a function to delete old row
create function func_tr_limit() returns trigger 
language plpgsql as $BODY$ 
begin 
	delete from limitation where timer <current_timestamp-interval '1 hour';
	return null; 
end; 
$BODY$

-- create a trigger to delete old row
create trigger tr_limit after insert
on limitation for each row
execute procedure func_tr_limit();