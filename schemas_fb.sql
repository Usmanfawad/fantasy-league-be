--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3
-- Dumped by pg_dump version 17.4

-- Started on 2025-08-23 13:33:14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 866 (class 1247 OID 84730)
-- Name: userrole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'MANAGER',
    'USER'
);


ALTER TYPE public.userrole OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 218 (class 1259 OID 85811)
-- Name: admins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admins (
    admin_id integer NOT NULL,
    username character varying NOT NULL,
    hashed_password character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.admins OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 85810)
-- Name: admins_admin_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admins_admin_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admins_admin_id_seq OWNER TO postgres;

--
-- TOC entry 4927 (class 0 OID 0)
-- Dependencies: 217
-- Name: admins_admin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admins_admin_id_seq OWNED BY public.admins.admin_id;


--
-- TOC entry 231 (class 1259 OID 85900)
-- Name: events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.events (
    event_id integer NOT NULL,
    player_id integer NOT NULL,
    gw_id integer NOT NULL,
    event_type character varying NOT NULL,
    fixture_id integer NOT NULL,
    minute integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.events OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 85899)
-- Name: events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.events_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.events_event_id_seq OWNER TO postgres;

--
-- TOC entry 4928 (class 0 OID 0)
-- Dependencies: 230
-- Name: events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.events_event_id_seq OWNED BY public.events.event_id;


--
-- TOC entry 226 (class 1259 OID 85847)
-- Name: fixtures; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fixtures (
    fixture_id integer NOT NULL,
    gw_id integer NOT NULL,
    home_team_id integer NOT NULL,
    away_team_id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    home_team_score integer NOT NULL,
    away_team_score integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.fixtures OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 85846)
-- Name: fixtures_fixture_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.fixtures_fixture_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fixtures_fixture_id_seq OWNER TO postgres;

--
-- TOC entry 4929 (class 0 OID 0)
-- Dependencies: 225
-- Name: fixtures_fixture_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.fixtures_fixture_id_seq OWNED BY public.fixtures.fixture_id;


--
-- TOC entry 220 (class 1259 OID 85820)
-- Name: gameweeks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gameweeks (
    gw_id integer NOT NULL,
    gw_number integer NOT NULL,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    status character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.gameweeks OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 85819)
-- Name: gameweeks_gw_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gameweeks_gw_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gameweeks_gw_id_seq OWNER TO postgres;

--
-- TOC entry 4930 (class 0 OID 0)
-- Dependencies: 219
-- Name: gameweeks_gw_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gameweeks_gw_id_seq OWNED BY public.gameweeks.gw_id;


--
-- TOC entry 237 (class 1259 OID 85973)
-- Name: manager_activity_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.manager_activity_logs (
    log_id integer NOT NULL,
    manager_id integer NOT NULL,
    action character varying NOT NULL,
    context jsonb,
    ip_adress character varying,
    user_agent character varying,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.manager_activity_logs OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 85972)
-- Name: manager_activity_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.manager_activity_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.manager_activity_logs_log_id_seq OWNER TO postgres;

--
-- TOC entry 4931 (class 0 OID 0)
-- Dependencies: 236
-- Name: manager_activity_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.manager_activity_logs_log_id_seq OWNED BY public.manager_activity_logs.log_id;


--
-- TOC entry 241 (class 1259 OID 86039)
-- Name: manager_gameweek_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.manager_gameweek_state (
    manager_id integer NOT NULL,
    gw_id integer NOT NULL,
    free_transfers integer DEFAULT 1 NOT NULL,
    transfers_made integer DEFAULT 0 NOT NULL,
    transfers_budget numeric DEFAULT 0.0 NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.manager_gameweek_state OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 85924)
-- Name: managers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.managers (
    manager_id integer NOT NULL,
    mng_firstname character varying NOT NULL,
    mng_lastname character varying NOT NULL,
    squad_name character varying NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    birthdate timestamp without time zone,
    city character varying,
    fav_team_id integer,
    fav_player_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    mng_datapoint character varying NOT NULL,
    wallet integer NOT NULL
);


ALTER TABLE public.managers OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 85923)
-- Name: managers_manager_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.managers_manager_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.managers_manager_id_seq OWNER TO postgres;

--
-- TOC entry 4932 (class 0 OID 0)
-- Dependencies: 232
-- Name: managers_manager_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.managers_manager_id_seq OWNED BY public.managers.manager_id;


--
-- TOC entry 238 (class 1259 OID 85986)
-- Name: managers_squad; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.managers_squad (
    manager_id integer NOT NULL,
    player_id integer NOT NULL,
    gw_id integer NOT NULL,
    is_captain boolean NOT NULL,
    is_vice_captain boolean NOT NULL,
    is_starter boolean NOT NULL
);


ALTER TABLE public.managers_squad OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 85942)
-- Name: player_prices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.player_prices (
    player_id integer NOT NULL,
    gw_id integer NOT NULL,
    price numeric(5,2) NOT NULL,
    transfers_in integer NOT NULL,
    transfers_out integer NOT NULL,
    net_transfers integer NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    selected integer NOT NULL
);


ALTER TABLE public.player_prices OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 85957)
-- Name: player_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.player_stats (
    player_id integer NOT NULL,
    gw_id integer NOT NULL,
    total_points integer NOT NULL,
    goals_scored integer NOT NULL,
    assists integer NOT NULL,
    yellow_cards integer NOT NULL,
    red_cards integer NOT NULL,
    clean_sheets integer NOT NULL,
    bonus_points integer NOT NULL,
    minutes_played integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    started boolean NOT NULL
);


ALTER TABLE public.player_stats OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 85869)
-- Name: players; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.players (
    player_id integer NOT NULL,
    player_firstname character varying NOT NULL,
    player_lastname character varying NOT NULL,
    player_fullname character varying NOT NULL,
    player_pic_url character varying NOT NULL,
    team_id integer NOT NULL,
    position_id integer NOT NULL,
    initial_price numeric(5,2) NOT NULL,
    current_price numeric(5,2) NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.players OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 85868)
-- Name: players_player_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.players_player_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.players_player_id_seq OWNER TO postgres;

--
-- TOC entry 4933 (class 0 OID 0)
-- Dependencies: 227
-- Name: players_player_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.players_player_id_seq OWNED BY public.players.player_id;


--
-- TOC entry 222 (class 1259 OID 85829)
-- Name: positions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.positions (
    position_id integer NOT NULL,
    position_name character varying NOT NULL
);


ALTER TABLE public.positions OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 85828)
-- Name: positions_position_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.positions_position_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.positions_position_id_seq OWNER TO postgres;

--
-- TOC entry 4934 (class 0 OID 0)
-- Dependencies: 221
-- Name: positions_position_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.positions_position_id_seq OWNED BY public.positions.position_id;


--
-- TOC entry 229 (class 1259 OID 85887)
-- Name: scoring_rules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scoring_rules (
    event_type character varying NOT NULL,
    position_id integer NOT NULL,
    points integer NOT NULL
);


ALTER TABLE public.scoring_rules OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 85838)
-- Name: teams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teams (
    team_id integer NOT NULL,
    team_name character varying NOT NULL,
    team_shortname character varying NOT NULL,
    team_logo_url character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.teams OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 85837)
-- Name: teams_team_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teams_team_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teams_team_id_seq OWNER TO postgres;

--
-- TOC entry 4935 (class 0 OID 0)
-- Dependencies: 223
-- Name: teams_team_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teams_team_id_seq OWNED BY public.teams.team_id;


--
-- TOC entry 240 (class 1259 OID 86007)
-- Name: transfers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transfers (
    transfer_id integer NOT NULL,
    manager_id integer NOT NULL,
    player_in_id integer NOT NULL,
    player_out_id integer NOT NULL,
    gw_id integer NOT NULL,
    transfer_time timestamp without time zone NOT NULL
);


ALTER TABLE public.transfers OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 86006)
-- Name: transfers_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transfers_transfer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transfers_transfer_id_seq OWNER TO postgres;

--
-- TOC entry 4936 (class 0 OID 0)
-- Dependencies: 239
-- Name: transfers_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transfers_transfer_id_seq OWNED BY public.transfers.transfer_id;


--
-- TOC entry 216 (class 1259 OID 84738)
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    email character varying NOT NULL,
    is_active boolean NOT NULL,
    role public.userrole NOT NULL,
    id integer NOT NULL,
    hashed_password character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- TOC entry 215 (class 1259 OID 84737)
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO postgres;

--
-- TOC entry 4937 (class 0 OID 0)
-- Dependencies: 215
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- TOC entry 4708 (class 2604 OID 85814)
-- Name: admins admin_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins ALTER COLUMN admin_id SET DEFAULT nextval('public.admins_admin_id_seq'::regclass);


--
-- TOC entry 4714 (class 2604 OID 85903)
-- Name: events event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events ALTER COLUMN event_id SET DEFAULT nextval('public.events_event_id_seq'::regclass);


--
-- TOC entry 4712 (class 2604 OID 85850)
-- Name: fixtures fixture_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fixtures ALTER COLUMN fixture_id SET DEFAULT nextval('public.fixtures_fixture_id_seq'::regclass);


--
-- TOC entry 4709 (class 2604 OID 85823)
-- Name: gameweeks gw_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gameweeks ALTER COLUMN gw_id SET DEFAULT nextval('public.gameweeks_gw_id_seq'::regclass);


--
-- TOC entry 4716 (class 2604 OID 85976)
-- Name: manager_activity_logs log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manager_activity_logs ALTER COLUMN log_id SET DEFAULT nextval('public.manager_activity_logs_log_id_seq'::regclass);


--
-- TOC entry 4715 (class 2604 OID 85927)
-- Name: managers manager_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers ALTER COLUMN manager_id SET DEFAULT nextval('public.managers_manager_id_seq'::regclass);


--
-- TOC entry 4713 (class 2604 OID 85872)
-- Name: players player_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.players ALTER COLUMN player_id SET DEFAULT nextval('public.players_player_id_seq'::regclass);


--
-- TOC entry 4710 (class 2604 OID 85832)
-- Name: positions position_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.positions ALTER COLUMN position_id SET DEFAULT nextval('public.positions_position_id_seq'::regclass);


--
-- TOC entry 4711 (class 2604 OID 85841)
-- Name: teams team_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams ALTER COLUMN team_id SET DEFAULT nextval('public.teams_team_id_seq'::regclass);


--
-- TOC entry 4717 (class 2604 OID 86010)
-- Name: transfers transfer_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfers ALTER COLUMN transfer_id SET DEFAULT nextval('public.transfers_transfer_id_seq'::regclass);


--
-- TOC entry 4707 (class 2604 OID 84741)
-- Name: user id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- TOC entry 4725 (class 2606 OID 85818)
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (admin_id);


--
-- TOC entry 4739 (class 2606 OID 85907)
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (event_id);


--
-- TOC entry 4733 (class 2606 OID 85852)
-- Name: fixtures fixtures_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fixtures
    ADD CONSTRAINT fixtures_pkey PRIMARY KEY (fixture_id);


--
-- TOC entry 4727 (class 2606 OID 85827)
-- Name: gameweeks gameweeks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gameweeks
    ADD CONSTRAINT gameweeks_pkey PRIMARY KEY (gw_id);


--
-- TOC entry 4747 (class 2606 OID 85980)
-- Name: manager_activity_logs manager_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manager_activity_logs
    ADD CONSTRAINT manager_activity_logs_pkey PRIMARY KEY (log_id);


--
-- TOC entry 4753 (class 2606 OID 86048)
-- Name: manager_gameweek_state manager_gameweek_state_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manager_gameweek_state
    ADD CONSTRAINT manager_gameweek_state_pk PRIMARY KEY (manager_id, gw_id);


--
-- TOC entry 4741 (class 2606 OID 85931)
-- Name: managers managers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers
    ADD CONSTRAINT managers_pkey PRIMARY KEY (manager_id);


--
-- TOC entry 4749 (class 2606 OID 85990)
-- Name: managers_squad managers_squad_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers_squad
    ADD CONSTRAINT managers_squad_pkey PRIMARY KEY (manager_id, player_id, gw_id);


--
-- TOC entry 4743 (class 2606 OID 85946)
-- Name: player_prices player_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_prices
    ADD CONSTRAINT player_prices_pkey PRIMARY KEY (player_id, gw_id);


--
-- TOC entry 4745 (class 2606 OID 85961)
-- Name: player_stats player_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_pkey PRIMARY KEY (player_id, gw_id);


--
-- TOC entry 4735 (class 2606 OID 85876)
-- Name: players players_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_pkey PRIMARY KEY (player_id);


--
-- TOC entry 4729 (class 2606 OID 85836)
-- Name: positions positions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.positions
    ADD CONSTRAINT positions_pkey PRIMARY KEY (position_id);


--
-- TOC entry 4737 (class 2606 OID 85893)
-- Name: scoring_rules scoring_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scoring_rules
    ADD CONSTRAINT scoring_rules_pkey PRIMARY KEY (event_type, position_id);


--
-- TOC entry 4731 (class 2606 OID 85845)
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (team_id);


--
-- TOC entry 4751 (class 2606 OID 86012)
-- Name: transfers transfers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfers
    ADD CONSTRAINT transfers_pkey PRIMARY KEY (transfer_id);


--
-- TOC entry 4723 (class 2606 OID 84745)
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- TOC entry 4721 (class 1259 OID 84746)
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- TOC entry 4760 (class 2606 OID 85918)
-- Name: events events_fixture_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_fixture_id_fkey FOREIGN KEY (fixture_id) REFERENCES public.fixtures(fixture_id);


--
-- TOC entry 4761 (class 2606 OID 85913)
-- Name: events events_gw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_gw_id_fkey FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4762 (class 2606 OID 85908)
-- Name: events events_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(player_id);


--
-- TOC entry 4754 (class 2606 OID 85863)
-- Name: fixtures fixtures_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fixtures
    ADD CONSTRAINT fixtures_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(team_id);


--
-- TOC entry 4755 (class 2606 OID 85853)
-- Name: fixtures fixtures_gw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fixtures
    ADD CONSTRAINT fixtures_gw_id_fkey FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4756 (class 2606 OID 85858)
-- Name: fixtures fixtures_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fixtures
    ADD CONSTRAINT fixtures_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(team_id);


--
-- TOC entry 4769 (class 2606 OID 85981)
-- Name: manager_activity_logs manager_activity_logs_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manager_activity_logs
    ADD CONSTRAINT manager_activity_logs_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.managers(manager_id);


--
-- TOC entry 4777 (class 2606 OID 86054)
-- Name: manager_gameweek_state manager_gameweek_state_gameweeks_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manager_gameweek_state
    ADD CONSTRAINT manager_gameweek_state_gameweeks_fk FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4778 (class 2606 OID 86049)
-- Name: manager_gameweek_state manager_gameweek_state_managers_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manager_gameweek_state
    ADD CONSTRAINT manager_gameweek_state_managers_fk FOREIGN KEY (manager_id) REFERENCES public.managers(manager_id);


--
-- TOC entry 4763 (class 2606 OID 85937)
-- Name: managers managers_fav_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers
    ADD CONSTRAINT managers_fav_player_id_fkey FOREIGN KEY (fav_player_id) REFERENCES public.players(player_id);


--
-- TOC entry 4764 (class 2606 OID 85932)
-- Name: managers managers_fav_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers
    ADD CONSTRAINT managers_fav_team_id_fkey FOREIGN KEY (fav_team_id) REFERENCES public.teams(team_id);


--
-- TOC entry 4770 (class 2606 OID 86001)
-- Name: managers_squad managers_squad_gw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers_squad
    ADD CONSTRAINT managers_squad_gw_id_fkey FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4771 (class 2606 OID 85991)
-- Name: managers_squad managers_squad_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers_squad
    ADD CONSTRAINT managers_squad_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.managers(manager_id);


--
-- TOC entry 4772 (class 2606 OID 85996)
-- Name: managers_squad managers_squad_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.managers_squad
    ADD CONSTRAINT managers_squad_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(player_id);


--
-- TOC entry 4765 (class 2606 OID 85952)
-- Name: player_prices player_prices_gw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_prices
    ADD CONSTRAINT player_prices_gw_id_fkey FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4766 (class 2606 OID 85947)
-- Name: player_prices player_prices_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_prices
    ADD CONSTRAINT player_prices_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(player_id);


--
-- TOC entry 4767 (class 2606 OID 85967)
-- Name: player_stats player_stats_gw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_gw_id_fkey FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4768 (class 2606 OID 85962)
-- Name: player_stats player_stats_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(player_id);


--
-- TOC entry 4757 (class 2606 OID 85882)
-- Name: players players_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_position_id_fkey FOREIGN KEY (position_id) REFERENCES public.positions(position_id);


--
-- TOC entry 4758 (class 2606 OID 85877)
-- Name: players players_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(team_id);


--
-- TOC entry 4759 (class 2606 OID 85894)
-- Name: scoring_rules scoring_rules_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scoring_rules
    ADD CONSTRAINT scoring_rules_position_id_fkey FOREIGN KEY (position_id) REFERENCES public.positions(position_id);


--
-- TOC entry 4773 (class 2606 OID 86028)
-- Name: transfers transfers_gw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfers
    ADD CONSTRAINT transfers_gw_id_fkey FOREIGN KEY (gw_id) REFERENCES public.gameweeks(gw_id);


--
-- TOC entry 4774 (class 2606 OID 86013)
-- Name: transfers transfers_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfers
    ADD CONSTRAINT transfers_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.managers(manager_id);


--
-- TOC entry 4775 (class 2606 OID 86018)
-- Name: transfers transfers_player_in_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfers
    ADD CONSTRAINT transfers_player_in_id_fkey FOREIGN KEY (player_in_id) REFERENCES public.players(player_id);


--
-- TOC entry 4776 (class 2606 OID 86023)
-- Name: transfers transfers_player_out_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfers
    ADD CONSTRAINT transfers_player_out_id_fkey FOREIGN KEY (player_out_id) REFERENCES public.players(player_id);


-- Completed on 2025-08-23 13:33:14

--
-- PostgreSQL database dump complete
--

