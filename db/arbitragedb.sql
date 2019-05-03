-- MySQL dump 10.13  Distrib 5.7.23, for osx10.14 (x86_64)
--
-- Host: arbitrage-db.cwa7djjjkb6f.eu-west-2.rds.amazonaws.com    Database: arbitragedb
-- ------------------------------------------------------
-- Server version	5.6.41-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `arbitrage`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `arbitrage` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(100) DEFAULT NULL,
  `exchange_id` varchar(100) DEFAULT NULL,
  `exchange_name` varchar(100) DEFAULT NULL,
  `volumeBase` decimal(40,20) DEFAULT NULL,
  `limitPrice` decimal(40,20) DEFAULT NULL,
  `symbol` varchar(100) DEFAULT NULL,
  `meanPrice` decimal(40,20) DEFAULT NULL,
  `shouldAbort` bit(1) DEFAULT NULL,
  `status` varchar(100) DEFAULT NULL,
  `type` varchar(100) DEFAULT NULL,
  `json` longtext,
  PRIMARY KEY (`id`),
  KEY `arbitrage_uuid_IDX` (`uuid`) USING BTREE,
  KEY `arbitrage_exchange_id_IDX` (`exchange_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `arbitrage_history`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `arbitrage_history` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(100) DEFAULT NULL,
  `exchange_name` varchar(100) DEFAULT NULL,
  `exchange_id` varchar(100) DEFAULT NULL,
  `status` varchar(100) DEFAULT NULL,
  `time` timestamp NULL DEFAULT NULL,
  `dtime` float DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `arbitrage_history_exchange_id_IDX` (`exchange_id`) USING BTREE,
  KEY `arbitrage_history_uuid_IDX` (`uuid`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `balance`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `balance` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(255) DEFAULT NULL,
  `timing` tinyint(4) DEFAULT NULL,
  `exchange` varchar(255) DEFAULT NULL,
  `symbol` varchar(255) DEFAULT NULL,
  `balance` decimal(50,25) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=341 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `order`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `order` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `exchange` varchar(100) NOT NULL,
  `exchange_id` varchar(128) NOT NULL,
  `status` varchar(100) NOT NULL,
  `timestamp` bigint(20) unsigned DEFAULT NULL,
  `datetime` datetime DEFAULT NULL,
  `symbol` varchar(100) NOT NULL,
  `type` varchar(100) NOT NULL,
  `side` varchar(100) NOT NULL,
  `price` decimal(40,20) NOT NULL,
  `cost` decimal(40,20) DEFAULT NULL,
  `amount` decimal(40,20) DEFAULT NULL,
  `filled` decimal(40,20) DEFAULT NULL,
  `remaining` decimal(40,20) DEFAULT NULL,
  `fee_cost` decimal(40,20) DEFAULT NULL,
  `fee_currency` varchar(100) DEFAULT NULL,
  `fee_rate` decimal(40,20) DEFAULT NULL,
  `json` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_exchange_IDX` (`exchange`,`exchange_id`,`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7160 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trade`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `trade` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `exchange` varchar(100) NOT NULL,
  `exchange_id` varchar(128) NOT NULL,
  `exchange_order_id` varchar(128) NOT NULL,
  `timestamp` bigint(20) unsigned DEFAULT NULL,
  `datetime` datetime DEFAULT NULL,
  `symbol` varchar(100) NOT NULL,
  `type` varchar(100) NOT NULL,
  `side` varchar(100) NOT NULL,
  `price` decimal(40,20) NOT NULL,
  `cost` decimal(40,20) DEFAULT NULL,
  `amount` decimal(40,20) DEFAULT NULL,
  `fee_cost` decimal(40,20) DEFAULT NULL,
  `fee_currency` varchar(100) DEFAULT NULL,
  `fee_rate` decimal(40,20) DEFAULT NULL,
  `json` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_exchange_IDX` (`exchange`,`exchange_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=4813 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `uuid`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `uuid` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(100) DEFAULT NULL,
  `txt` longtext,
  PRIMARY KEY (`id`),
  KEY `uuid_uuid_IDX` (`uuid`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `uuid_balance_diff`
--

SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `uuid_balance_diff` AS SELECT 
 1 AS `created_at`,
 1 AS `uuid`,
 1 AS `symbol`,
 1 AS `diff`*/;
SET character_set_client = @saved_cs_client;

--
-- Dumping routines for database 'arbitragedb'
--

--
-- Final view structure for view `uuid_balance_diff`
--

/*!50001 DROP VIEW IF EXISTS `uuid_balance_diff`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`admin`@`%` SQL SECURITY DEFINER */
/*!50001 VIEW `uuid_balance_diff` AS select `balance`.`created_at` AS `created_at`,`balance`.`uuid` AS `uuid`,`balance`.`symbol` AS `symbol`,sum((`balance`.`timing` * `balance`.`balance`)) AS `diff` from `balance` where (`balance`.`uuid` is not null) group by `balance`.`uuid`,`balance`.`symbol` having (abs(`diff`) > 0) order by `balance`.`created_at` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2019-05-03 18:45:31
