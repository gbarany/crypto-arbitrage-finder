select * from balance where uuid is not null;
select created_at, uuid from balance where uuid is not null group by uuid order by created_at;
select * from balance where uuid like "0b039bc9-8c00-47cf-bc39-efd4298aceac";
select *, count(*) from balance where uuid is not null group by uuid, exchange, symbol order by uuid, exchange, symbol, timing ;
select *, count(*) from balance where uuid like "0b039bc9-8c00-47cf-bc39-efd4298aceac" group by uuid, exchange, symbol order by uuid, exchange, symbol, timing ;
select *, timing*balance from balance where uuid like "0b039bc9-8c00-47cf-bc39-efd4298aceac" order by uuid, exchange, symbol, timing ;
select created_at, uuid, exchange, symbol, sum(timing*balance) as diff 
	from balance 
	where uuid like "0b039bc9-8c00-47cf-bc39-efd4298aceac"
	group by uuid, exchange, symbol
	having abs(diff) > 0
	order by uuid, exchange, symbol, timing ;

select created_at, uuid, exchange, symbol, sum(timing*balance) as diff 
	from balance 
	where uuid like "0b039bc9-8c00-47cf-bc39-efd4298aceac"
	group by uuid, symbol
	having abs(diff) > 0
	order by uuid, exchange, symbol, timing ;

select created_at, uuid, exchange, symbol, sum(timing*balance) as diff 
	from balance 
	where uuid is not null
	group by uuid, exchange, symbol
	having abs(diff) > 0
	order by uuid, exchange, symbol, timing ;

create or replace view uuid_balance_diff as
	select created_at, uuid, symbol, sum(timing*balance) as diff 
	from balance 
	where uuid is not null
	group by uuid, symbol
	having abs(diff) > 0
	order by created_at ;

select * from uuid_balance_diff;